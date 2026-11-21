from playwright.sync_api import expect
from conftest import KEY, add_task, open_tasks, task

from datetime import datetime, timedelta, timezone
import pytest

def test_today_and_overdue_refresh_after_local_midnight(page, site):
    open_tasks(page, site, [task('Yesterday after midnight', '2026-11-21'), task('New today', '2026-11-22')])
    page.locator('[data-view="today"]').click()
    expect(page.locator('.task-title')).to_have_text(['Yesterday after midnight'])
    page.clock.set_system_time(datetime(2026, 11, 22, 0, 1, tzinfo=timezone(timedelta(hours=5, minutes=30))))
    page.clock.fast_forward(60000)
    expect(page.locator('#header-date')).to_contain_text('Nov 22')
    expect(page.locator('.task-title')).to_have_text(['New today'])
    page.locator('[data-view="all"]').click()
    expect(page.locator('.overdue')).to_have_text('Nov 21, 2026')


def test_extended_year_is_rejected_before_it_can_corrupt_saved_tasks(page, site):
    open_tasks(page, site, [])
    page.locator('#add-task').click()
    page.locator('#task-title').fill('Out of range')
    page.locator('#task-due').fill('10000-01-01')
    page.get_by_role('button', name='Save task').click()
    expect(page.locator('#task-modal')).to_be_visible()
    expect(page.locator('#stat-total')).to_have_text('0')


def test_leap_day_and_year_end_survive_reload(page, site):
    open_tasks(page, site, [])
    add_task(page, 'Leap day', '2028-02-29')
    add_task(page, 'Year end', '2026-12-31')
    page.reload()
    page.locator('#sort').select_option('due')
    expect(page.locator('.due-date')).to_have_text(['Dec 31, 2026', 'Feb 29, 2028'])


@pytest.mark.parametrize('due', ['2026-02-29', '2026-02-31', '0000-01-01', '2026-13-01'])
def test_impossible_saved_dates_do_not_display_as_a_different_day(page, site, due):
    open_tasks(page, site, [task('Invalid date', due)])
    expect(page.locator('#storage-error')).to_be_visible()
    expect(page.locator('#add-task')).to_be_disabled()

