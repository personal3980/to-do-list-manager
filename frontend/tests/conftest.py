"""Real Chromium tests with isolated storage and mocked auth/CDN transport."""
import functools
import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import urlopen

import pytest
from playwright.sync_api import sync_playwright

FRONTEND = Path(__file__).resolve().parents[1]
USER = {'id': 1, 'name': 'QA User', 'email': 'qa@example.com'}
KEY = 'taskwell.tasks.user.1.v1'


@pytest.fixture(scope='session')
def site():
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(FRONTEND)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.fixture(scope='session')
def assets():
    urls = {
        'https://code.jquery.com/jquery-3.7.1.min.js': 'jquery.js',
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css': 'bootstrap.css',
        'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js': 'bootstrap.js',
    }
    cache = FRONTEND.parent / '.qa-cache'
    cache.mkdir(exist_ok=True)
    result = {}
    for url, filename in urls.items():
        path = cache / filename
        if not path.exists():
            path.write_bytes(urlopen(url, timeout=30).read())
        result[url] = path.read_bytes()
    return result


@pytest.fixture(scope='session')
def browser():
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def page(browser, site, assets, request):
    context = browser.new_context(viewport={'width': 1366, 'height': 900},
                                  timezone_id=getattr(request, 'param', 'Asia/Kolkata'), locale='en-US', reduced_motion='reduce')
    def route(request):
        url = request.request.url
        if url in assets:
            request.fulfill(body=assets[url], content_type='text/css' if '.css' in url else 'application/javascript')
        elif ':8000/api/auth/' in url:
            headers = {'Access-Control-Allow-Origin': site, 'Access-Control-Allow-Credentials': 'true',
                       'Access-Control-Allow-Headers': 'content-type', 'Access-Control-Allow-Methods': 'GET, POST'}
            request.fulfill(status=200, json=USER if url.endswith(('/me', '/login')) else {'message': 'Done.'}, headers=headers)
        elif 'fonts.googleapis.com' in url or 'fonts.gstatic.com' in url:
            request.fulfill(body='', content_type='text/css')
        else:
            request.continue_()
    context.route('**/*', route)
    page = context.new_page()
    page.clock.install(time=page.evaluate('new Date(2026, 10, 21, 12).getTime() / 1000'))
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.qa_errors = errors
    yield page
    context.close()


def task(title, due='', **changes):
    return {'id': title, 'title': title, 'notes': '', 'priority': 'medium', 'due': due,
            'completed': False, 'createdAt': 1, **changes}


def open_tasks(page, site, tasks):
    page.goto(f'{site}/index.html')
    page.locator('#add-task').wait_for(state='visible')
    page.evaluate('([key, tasks]) => localStorage.setItem(key, JSON.stringify(tasks))', [KEY, tasks])
    page.reload()
    page.locator('#add-task').wait_for(state='visible')


def add_task(page, title, due=''):
    page.locator('#add-task').click()
    page.locator('#task-title').fill(title)
    if due:
        page.locator('#task-due').fill(due)
    page.get_by_role('button', name='Save task').click()
    page.locator('#task-modal').wait_for(state='hidden')
