"""Opt-in browser/API/MySQL test. Creates and removes only one unique QA user."""
import os
import re
import secrets
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

import httpx
import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.skipif(os.getenv('TASKWELL_TEST_MYSQL') != '1',
                                reason='Set TASKWELL_TEST_MYSQL=1 to test the configured local MySQL database.')

def test_live_signup_login_reset_and_logout(page, site):
    from sqlalchemy import delete, inspect, select
    from app.database import SessionLocal, engine
    from app.models import AuthSession, PasswordReset, User

    root = Path(__file__).resolve().parents[1]
    backend = root / 'backend'
    try:
        names = inspect(engine).get_table_names()
    except Exception as error:
        pytest.fail(f'Local MySQL is unavailable ({type(error).__name__}); credentials were not printed.')
    assert {'users', 'auth_sessions', 'password_reset_tokens'} <= set(names)
    inspector = inspect(engine)
    assert any(constraint['column_names'] == ['email'] for constraint in inspector.get_unique_constraints('users'))
    for table in ('auth_sessions', 'password_reset_tokens'):
        assert any(key['referred_table'] == 'users' and key['options'].get('ondelete') == 'CASCADE'
                   for key in inspector.get_foreign_keys(table))
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        port = sock.getsockname()[1]
    api = f'http://127.0.0.1:{port}/api/auth'
    email = f'qa-{secrets.token_hex(8)}@example.com'
    email_files = []
    existing_files = set((backend / 'reset-emails').glob('*.eml'))
    environment = {**os.environ, 'FRONTEND_ORIGIN': site, 'RESET_DELIVERY': 'local'}
    # Keep the user's existing server/ports and .env unchanged.
    log_path = root / 'test-results' / 'mysql-api.log'
    log_path.parent.mkdir(exist_ok=True)
    with log_path.open('w') as log:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app',
                                    '--host', '127.0.0.1', '--port', str(port)],
                                   cwd=backend, env=environment, stdout=log, stderr=log)
        try:
            for _ in range(100):
                if process.poll() is not None:
                    pytest.fail('The QA API failed to start; see ignored test-results/mysql-api.log.')
                try:
                    urlopen(f'http://127.0.0.1:{port}/openapi.json', timeout=0.2).close()
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                pytest.fail('The QA API did not become ready.')

            page.route('**/js/config.js*', lambda route: route.fulfill(
                body=f'window.TASKWELL_API = "{api}";', content_type='application/javascript'))
            page.goto(f'{site}/signup.html')
            page.locator('#name').fill('Temporary QA User')
            page.locator('#email').fill(email)
            page.locator('#password').fill('QaPassword123')
            page.locator('#confirm_password').fill('QaPassword123')
            page.get_by_role('button', name='Create account').click()
            expect(page).to_have_url(f'{site}/login.html?registered=1')
            page.locator('#email').fill(email)
            page.locator('#password').fill('QaPassword123')
            page.get_by_role('button', name='Log in', exact=True).click()
            expect(page).to_have_url(f'{site}/index.html')
            expect(page.locator('.account-name')).to_have_text('Temporary QA User')
            page.goto(f'{site}/forgot-password.html')
            page.locator('#email').fill(email)
            page.get_by_role('button', name='Send reset link').click()
            expect(page.locator('#auth-message')).to_contain_text('If an account exists')
            for path in set((backend / 'reset-emails').glob('*.eml')) - existing_files:
                text = path.read_text(encoding='utf-8')
                if f'To: {email}' in text:
                    email_files.append(path)
                    token = re.search(r'#token=([A-Za-z0-9_-]{43})', text).group(1)
            assert email_files, 'No local email preview was created for the QA user.'
            page.goto(f'{site}/reset-password.html#token={token}')
            page.locator('#password').fill('QaChangedPassword123')
            page.locator('#confirm_password').fill('QaChangedPassword123')
            page.get_by_role('button', name='Reset password').click()
            expect(page.locator('#auth-message')).to_contain_text('Password updated')
            with SessionLocal() as db:
                user = db.scalar(select(User).where(User.email == email))
                assert db.scalar(select(AuthSession).where(AuthSession.user_id == user.id)) is None
                assert db.scalar(select(PasswordReset).where(PasswordReset.user_id == user.id)) is None
            # Replay is rejected by the real MySQL-backed API.
            replay = httpx.post(f'{api}/reset-password', headers={'Origin': site}, json={
                'token': token, 'password': 'QaChangedPassword123', 'confirm_password': 'QaChangedPassword123'})
            assert replay.status_code == 400
            page.goto(f'{site}/login.html')
            page.locator('#email').fill(email)
            page.locator('#password').fill('QaPassword123')
            page.get_by_role('button', name='Log in', exact=True).click()
            expect(page.locator('#auth-message')).to_contain_text('incorrect')
            page.locator('#password').fill('QaChangedPassword123')
            page.get_by_role('button', name='Log in', exact=True).click()
            expect(page).to_have_url(f'{site}/index.html')
            page.locator('#logout').click()
            expect(page).to_have_url(f'{site}/login.html')
            # Exercise actual MySQL row locks with two simultaneous reset attempts.
            result = httpx.post(f'{api}/forgot-password', headers={'Origin': site}, json={'email': email})
            assert result.status_code == 200
            fresh_token = None
            for path in set((backend / 'reset-emails').glob('*.eml')) - existing_files - set(email_files):
                text = path.read_text(encoding='utf-8')
                if f'To: {email}' in text:
                    email_files.append(path)
                    fresh_token = re.search(r'#token=([A-Za-z0-9_-]{43})', text).group(1)
            assert fresh_token
            def reset_once():
                return httpx.post(f'{api}/reset-password', headers={'Origin': site}, json={
                    'token': fresh_token, 'password': 'QaFinalPassword123', 'confirm_password': 'QaFinalPassword123'},
                    timeout=10).status_code
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(lambda _: reset_once(), range(2)))
            assert sorted(results) == [200, 400]
            assert not page.qa_errors
        finally:
            process.terminate()
            process.wait(timeout=10)
            with SessionLocal() as db:
                user = db.scalar(select(User).where(User.email == email))
                if user:
                    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id))
                    db.execute(delete(PasswordReset).where(PasswordReset.user_id == user.id))
                    db.delete(user)
                    db.commit()
            for path in set((backend / 'reset-emails').glob('*.eml')) - existing_files:
                if f'To: {email}' in path.read_text(encoding='utf-8'):
                    path.unlink(missing_ok=True)
