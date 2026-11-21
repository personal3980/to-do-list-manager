from playwright.sync_api import expect
from conftest import KEY, add_task, open_tasks


def test_storage_warning_clears_after_a_successful_save(page, site):
    open_tasks(page, site, [])
    page.evaluate('''() => {
        window.qaOriginalSetItem = Storage.prototype.setItem;
        Storage.prototype.setItem = function () { throw new DOMException('Full', 'QuotaExceededError'); };
    }''')
    add_task(page, 'Session only')
    expect(page.locator('#storage-error')).to_contain_text('session only')
    page.evaluate('() => { Storage.prototype.setItem = window.qaOriginalSetItem; }')
    add_task(page, 'Now saved')
    expect(page.locator('#storage-error')).to_be_hidden()
    page.reload()
    expect(page.locator('.task-title')).to_have_text(['Now saved', 'Session only'])
