from playwright.sync_api import expect
from frontend.tests.support import open_tasks, task


def test_returning_to_tab_rechecks_revoked_session(page, site):
    open_tasks(page, site, [task('Private task')])
    page.route('**/api/auth/me', lambda route: route.fulfill(status=401, json={'detail': 'Session revoked.'},
        headers={'Access-Control-Allow-Origin': site, 'Access-Control-Allow-Credentials': 'true'}))
    page.evaluate("window.dispatchEvent(new Event('focus'))")
    expect(page).to_have_url(f'{site}/login.html')
