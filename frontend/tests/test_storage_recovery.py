from playwright.sync_api import expect
from conftest import KEY, add_task, open_tasks, task


def test_corrupted_saved_data_is_not_overwritten_by_a_new_task(page, site):
    open_tasks(page, site, [])
    page.evaluate('key => localStorage.setItem(key, "broken original data")', KEY)
    page.reload()
    expect(page.locator('#storage-error')).to_be_visible()
    expect(page.locator('#add-task')).to_be_disabled()
    assert page.evaluate('key => localStorage.getItem(key)', KEY) == 'broken original data'

