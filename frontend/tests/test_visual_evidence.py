from pathlib import Path

from frontend.tests.support import FRONTEND, open_tasks, task


def test_capture_dashboard_and_signup_layouts(page, site):
    output = FRONTEND.parent / 'test-results'
    output.mkdir(exist_ok=True)
    open_tasks(page, site, [task('Past due: review weekly plan', '2026-11-20', priority='high'),
        task('Today: prepare project notes', '2026-11-21'),
        task('Future: plan next month', '2026-12-01', priority='low'),
        task('Completed work', '2026-11-21', completed=True)])
    page.screenshot(path=str(output / 'dashboard-desktop.png'), full_page=True)
    page.set_viewport_size({'width': 375, 'height': 850})
    page.screenshot(path=str(output / 'dashboard-mobile.png'), full_page=True)
    page.goto(f'{site}/signup.html')
    page.screenshot(path=str(output / 'signup-mobile.png'), full_page=True)
    assert not page.qa_errors
