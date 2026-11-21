from playwright.sync_api import expect
from frontend.tests.support import KEY, add_task, open_tasks, task


def test_new_task_form_does_not_keep_previous_custom_validation(page, site):
    open_tasks(page, site, [])
    page.locator('#add-task').click()
    page.locator('#task-title').fill('   ')
    page.get_by_role('button', name='Save task').click()
    page.get_by_role('button', name='Cancel', exact=True).click()
    page.locator('#task-modal').wait_for(state='hidden')
    page.locator('#add-task').click()
    assert page.locator('#task-title').evaluate('(input) => input.validationMessage') != 'Enter a task title.'

