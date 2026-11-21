from playwright.sync_api import expect
from conftest import KEY, add_task, open_tasks, task


def test_two_tabs_preserve_each_others_changes(page, site):
    open_tasks(page, site, [])
    second = page.context.new_page()
    second.goto(f'{site}/index.html')
    second.locator('#add-task').wait_for(state='visible')
    add_task(page, 'First tab task')
    expect(second.locator('.task-title')).to_have_text(['First tab task'])
    add_task(second, 'Second tab task')
    expect(page.locator('.task-title')).to_have_text(['Second tab task', 'First tab task'])
    page.reload()
    expect(page.locator('.task-title')).to_have_count(2)
    second.close()
