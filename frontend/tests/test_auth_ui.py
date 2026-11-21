import pytest
from playwright.sync_api import expect

from conftest import open_tasks, task


def test_signup_validation_and_success(page, site):
    page.goto(f'{site}/signup.html')
    page.locator('#name').fill('QA User')
    page.locator('#email').fill('qa@example.com')
    page.locator('#password').fill('Password123')
    page.locator('#confirm_password').fill('Different123')
    page.get_by_role('button', name='Create account').click()
    assert page.locator('#confirm_password').evaluate('(el) => el.validationMessage') == 'Passwords do not match.'
    page.locator('#confirm_password').fill('Password123')
    page.get_by_role('button', name='Create account').click()
    expect(page).to_have_url(f'{site}/login.html?registered=1')
    expect(page.locator('#auth-message')).to_contain_text('Account created')


def test_login_failure_and_network_error_reenable_submit(page, site):
    page.goto(f'{site}/login.html')
    page.locator('#email').fill('qa@example.com')
    page.locator('#password').fill('WrongPassword123')
    def invalid(route):
        route.fulfill(status=401, json={'detail': 'Email or password is incorrect.'},
                      headers={'Access-Control-Allow-Origin': site, 'Access-Control-Allow-Credentials': 'true'})
    page.route('**/api/auth/login', invalid)
    page.get_by_role('button', name='Log in', exact=True).click()
    expect(page.locator('#auth-message')).to_have_text('Email or password is incorrect.')
    expect(page.get_by_role('button', name='Log in', exact=True)).to_be_enabled()
    page.route('**/api/auth/login', lambda route: route.abort())
    page.get_by_role('button', name='Log in', exact=True).click()
    expect(page.locator('#auth-message')).to_contain_text('Cannot reach')
    expect(page.get_by_role('button', name='Log in', exact=True)).to_be_enabled()


def test_reset_missing_token_and_successful_reset(page, site):
    page.goto(f'{site}/reset-password.html')
    expect(page.locator('#auth-message')).to_contain_text('missing or invalid')
    expect(page.locator('#password')).to_be_disabled()
    page.goto(f'{site}/reset-password.html#token=' + 'a' * 43)
    expect(page).to_have_url(f'{site}/reset-password.html')
    page.locator('#password').fill('NewPassword123')
    page.locator('#confirm_password').fill('NewPassword123')
    page.get_by_role('button', name='Reset password').click()
    expect(page.locator('#auth-message')).to_have_text('Done.')
    expect(page.locator('#password')).to_be_disabled()


def test_dashboard_logs_out_and_rejects_missing_session(page, site):
    open_tasks(page, site, [])
    page.locator('#logout').click()
    expect(page).to_have_url(f'{site}/login.html')
    page.route('**/api/auth/me', lambda route: route.fulfill(status=401, json={'detail': 'Please log in.'},
        headers={'Access-Control-Allow-Origin': site, 'Access-Control-Allow-Credentials': 'true'}))
    page.goto(f'{site}/index.html')
    expect(page).to_have_url(f'{site}/login.html')


@pytest.mark.parametrize('filename', ['index.html', 'login.html', 'signup.html', 'forgot-password.html', 'reset-password.html'])
@pytest.mark.parametrize('width', [320, 375, 768, 1366])
def test_responsive_pages_do_not_overflow(page, site, filename, width):
    page.set_viewport_size({'width': width, 'height': 850})
    page.goto(f'{site}/{filename}')
    if filename == 'index.html':
        page.locator('#add-task').wait_for(state='visible')
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'{filename} overflows at {width}px'
    assert not page.qa_errors
