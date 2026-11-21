from playwright.sync_api import expect
import pytest

from conftest import KEY, add_task, open_tasks, task


@pytest.mark.parametrize('page', ['Asia/Kolkata', 'America/Los_Angeles', 'Pacific/Kiritimati'], indirect=True)
def test_past_present_future_dates_filters_and_sort(page, site):
    open_tasks(page, site, [task('Past', '2026-11-20'), task('Today', '2026-11-21'),
                           task('Future', '2026-11-22'), task('Undated'),
                           task('Finished future', '2026-11-22', completed=True)])
    expect(page.locator('.overdue')).to_have_count(1)
    expect(page.locator('.overdue')).to_have_text('Nov 20, 2026')
    page.locator('[data-view="today"]').click()
    expect(page.locator('.task-title')).to_have_text(['Today'])
    page.locator('[data-view="upcoming"]').click()
    expect(page.locator('.task-title')).to_have_text(['Future'])
    page.locator('[data-view="all"]').click()
    page.locator('#sort').select_option('due')
    expect(page.locator('.task-title')).to_have_text(['Past', 'Today', 'Future', 'Finished future', 'Undated'])
    assert not page.qa_errors


def test_task_crud_search_completion_and_persistence(page, site):
    open_tasks(page, site, [])
    add_task(page, 'Plan tomorrow', '2026-11-22')
    page.locator('.edit-task').click()
    page.locator('#task-title').fill('Review plan')
    page.locator('#task-notes').fill('Bring the notes')
    page.locator('#task-priority').select_option('high')
    page.get_by_role('button', name='Save task').click()
    page.locator('#task-modal').wait_for(state='hidden')
    page.locator('#search').fill('NOTES')
    expect(page.locator('.task-title')).to_have_text(['Review plan'])
    page.locator('.task-check').check()
    expect(page.locator('#stat-progress')).to_have_text('100%')
    page.reload()
    expect(page.locator('.task-row.done')).to_have_count(1)
    page.on('dialog', lambda dialog: dialog.accept())
    page.locator('#clear-completed').click()
    page.reload()
    expect(page.locator('#stat-total')).to_have_text('0')
    assert not page.qa_errors


def test_task_content_is_text_not_executable_markup(page, site):
    title = '<img src=x onerror="window.qaXss=true">'
    open_tasks(page, site, [task(title)])
    expect(page.locator('.task-title')).to_have_text(title)
    assert page.evaluate('window.qaXss') is None
    assert page.locator('#task-list img').count() == 0


def test_account_storage_is_isolated(page, site):
    open_tasks(page, site, [task('Private to user one')])
    page.evaluate("localStorage.setItem('taskwell.tasks.user.2.v1', '[]')")
    page.reload()
    expect(page.locator('.task-title')).to_have_text(['Private to user one'])


def test_cancelled_delete_preserves_task(page, site):
    open_tasks(page, site, [task('Keep me')])
    page.on('dialog', lambda dialog: dialog.dismiss())
    page.locator('.delete-task').click()
    expect(page.locator('.task-title')).to_have_text(['Keep me'])

