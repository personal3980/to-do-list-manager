"""Isolated API tests: no real database, SMTP, or reset-email files are touched."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import config
from app.database import Base, get_db
from app.main import app
from app.models import AuthSession, PasswordReset, User, utcnow
from app.routes import auth
from app.security import limiter, token_hash


@pytest.fixture
def setup(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def override_db():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    limiter.events.clear()
    emails = []
    monkeypatch.setattr(auth, 'send_reset_email', lambda email, token: emails.append((email, token)))
    # No context manager: intentionally skip production MySQL startup hook.
    client = TestClient(app, base_url='http://localhost:8000', headers={'Origin': config.FRONTEND_ORIGIN})
    yield client, factory, emails
    client.close()
    app.dependency_overrides.clear()
    limiter.events.clear()
    engine.dispose()


def signup(client):
    return client.post('/api/auth/signup', json={
        'name': '  Alex Morgan  ', 'email': ' ALEX@example.com ',
        'password': 'Password123', 'confirm_password': 'Password123'})


def login(client, password='Password123'):
    return client.post('/api/auth/login', json={'email': 'alex@example.com', 'password': password})


def test_signup_login_logout(setup):
    client, factory, _ = setup
    assert client.get('/api/auth/me').status_code == 401
    result = signup(client)
    assert result.status_code == 201
    assert result.json()['name'] == 'Alex Morgan'
    assert result.json()['email'] == 'alex@example.com'
    assert 'password_hash' not in result.json()
    assert signup(client).status_code == 409
    assert login(client, 'incorrect').status_code == 401
    result = login(client)
    assert result.status_code == 200
    assert 'HttpOnly' in result.headers['set-cookie']
    assert 'SameSite=lax' in result.headers['set-cookie']
    token = client.cookies.get(config.COOKIE_NAME)
    with factory() as db:
        assert db.scalar(select(User)).password_hash != 'Password123'
        assert db.get(AuthSession, token_hash(token)) is not None
        assert db.get(AuthSession, token) is None
    assert client.get('/api/auth/me').status_code == 200
    assert client.post('/api/auth/logout', json={}).status_code == 200
    client.cookies.set(config.COOKIE_NAME, token)
    assert client.get('/api/auth/me').status_code == 401


@pytest.mark.parametrize('change', [
    {'name': ' '}, {'email': 'not-an-email'}, {'password': 'short'},
    {'password': 'abcdefgh', 'confirm_password': 'abcdefgh'},
    {'password': '12345678', 'confirm_password': '12345678'},
    {'confirm_password': 'Mismatch123'}, {'password': 'a' * 129},
])
def test_server_validation_without_frontend(setup, change):
    client, _, _ = setup
    data = {'name': 'Alex', 'email': 'alex@example.com', 'password': 'Password123', 'confirm_password': 'Password123'}
    data.update(change)
    response = client.post('/api/auth/signup', json=data)
    assert response.status_code == 422
    assert 'Password123' not in response.text
    assert '"input"' not in response.text


def test_reset_is_single_use_and_revokes_sessions(setup):
    client, factory, emails = setup
    signup(client)
    login(client)
    old_session = client.cookies.get(config.COOKIE_NAME)
    known = client.post('/api/auth/forgot-password', json={'email': 'alex@example.com'})
    unknown = client.post('/api/auth/forgot-password', json={'email': 'missing@example.com'})
    assert known.json() == unknown.json()
    assert len(emails) == 1
    token = emails[0][1]
    assert token not in known.text
    with factory() as db:
        assert db.get(PasswordReset, token_hash(token)) is not None
    payload = {'token': token, 'password': 'NewPassword123', 'confirm_password': 'NewPassword123'}
    assert client.post('/api/auth/reset-password', json=payload).status_code == 200
    assert client.post('/api/auth/reset-password', json=payload).status_code == 400
    client.cookies.set(config.COOKIE_NAME, old_session)
    assert client.get('/api/auth/me').status_code == 401
    assert login(client).status_code == 401
    assert login(client, 'NewPassword123').status_code == 200


def test_expired_tokens_and_sessions(setup):
    client, factory, emails = setup
    signup(client)
    login(client)
    client.post('/api/auth/forgot-password', json={'email': 'alex@example.com'})
    with factory() as db:
        for model in (AuthSession, PasswordReset):
            item = db.scalar(select(model))
            item.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    assert client.get('/api/auth/me').status_code == 401
    assert client.post('/api/auth/reset-password', json={
        'token': emails[0][1], 'password': 'NewPassword123', 'confirm_password': 'NewPassword123'}).status_code == 400


def test_origin_body_limits_and_throttling(setup):
    client, _, _ = setup
    assert client.post('/api/auth/logout', json={}, headers={'Origin': 'https://other.example'}).status_code == 403
    assert client.post('/api/auth/logout', content='{}', headers={'Content-Type': 'text/plain'}).status_code == 415
    assert client.post('/api/auth/login', content='x' * 8193, headers={'Content-Type': 'application/json'}).status_code == 413
    assert client.post('/api/auth/login', content='{', headers={'Content-Type': 'application/json'}).status_code == 422
    for _ in range(5):
        assert client.post('/api/auth/forgot-password', json={'email': 'missing@example.com'}).status_code == 200
    assert client.post('/api/auth/forgot-password', json={'email': 'missing@example.com'}).status_code == 429


def test_email_delivery_failure_does_not_reveal_account(setup, monkeypatch):
    client, factory, _ = setup
    signup(client)
    def fail(*args):
        raise OSError('Simulated email failure')
    monkeypatch.setattr(auth, 'send_reset_email', fail)
    response = client.post('/api/auth/forgot-password', json={'email': 'alex@example.com'})
    assert response.status_code == 200
    with factory() as db:
        assert db.scalar(select(PasswordReset)) is None


def test_local_email_preview_preserves_copyable_link(tmp_path, monkeypatch):
    from app import mail
    monkeypatch.setattr(mail, 'BACKEND_DIR', tmp_path)
    monkeypatch.setenv('RESET_DELIVERY', 'local')
    token = 'a' * 43
    mail.send_reset_email('alex@example.com', token)
    previews = list((tmp_path / 'reset-emails').glob('*.eml'))
    assert len(previews) == 1
    content = previews[0].read_text(encoding='utf-8')
    assert f'{config.FRONTEND_ORIGIN}/reset-password.html#token={token}' in content
    assert 'To: alex@example.com' in content
