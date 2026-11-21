from playwright.sync_api import expect
from conftest import open_tasks, task


def test_undated_tasks_sort_after_the_latest_supported_date(page, site):
    open_tasks(page, site, [task('No date'), task('Far future', '9999-12-31'), task('Soon', '2026-11-22')])
    page.locator('#sort').select_option('due')
    expect(page.locator('.task-title')).to_have_text(['Soon', 'Far future', 'No date'])
