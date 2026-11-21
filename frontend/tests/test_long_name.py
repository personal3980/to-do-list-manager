from frontend.tests.support import open_tasks


def test_maximum_length_account_name_fits_mobile_header(page, site):
    page.set_viewport_size({'width': 320, 'height': 850})
    page.route('**/api/auth/me', lambda route: route.fulfill(json={
        'id': 1, 'name': 'A' * 80, 'email': 'qa@example.com'},
        headers={'Access-Control-Allow-Origin': site, 'Access-Control-Allow-Credentials': 'true'}))
    open_tasks(page, site, [])
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
