from playwright.sync_api import expect
from conftest import KEY, add_task, open_tasks, task

from datetime import datetime, timedelta, timezone

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

