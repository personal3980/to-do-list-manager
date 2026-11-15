"""Task persistence, ownership, validation, and browser import regression tests."""
import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from test_auth import setup, signup, login


@pytest.fixture
def client(setup):
    client, _, _ = setup
    signup(client)
    login(client)
    return client


def create(client, **changes):
    return client.post('/api/tasks', json={'title': 'Plan release', **changes})


def test_full_task_lifecycle_and_persistence(client):
    response = create(client, notes='Checklist', priority='high', due='2026-12-31')
    assert response.status_code == 201
    task = response.json()
    assert 'user_id' not in task
    assert task['created_at'].endswith('Z')
    task_id = task['id']
    assert client.get('/api/tasks').json() == [task]
    updated = client.put('/api/tasks/' + task_id, json={
        'title': '  Ship release  ', 'notes': 'Done', 'priority': 'low', 'due': None,
        'completed': True})
    assert updated.status_code == 200
    assert updated.json()['title'] == 'Ship release'
    assert updated.json()['due'] is None
    assert client.patch('/api/tasks/' + task_id, json={'completed': False}).json()['completed'] is False
    client.post('/api/auth/logout', json={})
    assert client.get('/api/tasks').status_code == 401
    login(client)
    assert client.get('/api/tasks').json()[0]['title'] == 'Ship release'
    assert client.delete('/api/tasks/' + task_id).status_code == 204
    assert client.get('/api/tasks').json() == []
    assert client.delete('/api/tasks/' + task_id).status_code == 404


def test_ownership_and_clear_completed(client):
    task = create(client, completed=True).json()
    with TestClientWithoutStartup() as other:
        other.post('/api/auth/signup', json={'name': 'Other user', 'email': 'other@example.com',
                   'password': 'Password123', 'confirm_password': 'Password123'})
        other.post('/api/auth/login', json={'email': 'other@example.com', 'password': 'Password123'})
        assert other.get('/api/tasks').json() == []
        for method, data in [('put', {'title': 'Stolen'}), ('patch', {'completed': False}), ('delete', None)]:
            kwargs = {} if data is None else {'json': data}
            assert getattr(other, method)('/api/tasks/' + task['id'], **kwargs).status_code == 404
        active = create(other).json()
        create(other, completed=True)
        assert other.delete('/api/tasks/completed').status_code == 204
        assert [t['id'] for t in other.get('/api/tasks').json()] == [active['id']]
    assert client.get('/api/tasks').json() == [task]


class TestClientWithoutStartup:
    # Avoid lifespan's real MySQL engine, as in the auth suite.
    def __enter__(self):
        self.client = TestClient(app, base_url='http://localhost:8000', headers={'Origin': config.FRONTEND_ORIGIN})
        return self.client

    def __exit__(self, *args):
        self.client.close()


@pytest.mark.parametrize('changes', [
    {'title': ''}, {'title': '   '}, {'title': 'x' * 121}, {'notes': 'x' * 501},
    {'priority': 'urgent'}, {'due': '2026-02-30'}, {'due': '0999-12-31'}, {'completed': 'false'},
    {'user_id': 999}, {'title': None},
])
def test_validation(client, changes):
    assert create(client, **changes).status_code == 422
    assert client.get('/api/tasks').json() == []


def test_idempotent_import(client):
    body = {'legacy_id': 'browser-123', 'title': 'Old task', 'completed': True}
    first = client.post('/api/tasks/import', json=body)
    assert first.status_code == 200
    assert client.post('/api/tasks/import', json=body).json() == first.json()
    assert len(client.get('/api/tasks').json()) == 1
    assert client.delete('/api/tasks/completed').status_code == 204


@pytest.mark.parametrize('method,path,body', [
    ('get', '/api/tasks', None), ('post', '/api/tasks', {'title': 'Private'}),
    ('put', '/api/tasks/missing', {'title': 'Private'}),
    ('patch', '/api/tasks/missing', {'completed': True}),
    ('delete', '/api/tasks/completed', None), ('delete', '/api/tasks/missing', None),
    ('post', '/api/tasks/import', {'title': 'Old', 'legacy_id': '123'}),
])
def test_requires_session(setup, method, path, body):
    client, _, _ = setup
    assert getattr(client, method)(path, **({} if body is None else {'json': body})).status_code == 401


@pytest.mark.parametrize('method,body', [('put', {'title': 'Bad'}), ('patch', {'completed': True}), ('delete', None)])
def test_mutation_origins(client, method, body):
    task = create(client).json()
    response = getattr(client, method)('/api/tasks/' + task['id'], headers={'Origin': 'https://untrusted.example'},
                                       **({} if body is None else {'json': body}))
    assert response.status_code == 403
    assert client.get('/api/tasks').json() == [task]


def test_preflight_supports_task_updates(client):
    for method in ['PUT', 'PATCH', 'DELETE']:
        result = client.options('/api/tasks/example', headers={
            'Origin': config.FRONTEND_ORIGIN, 'Access-Control-Request-Method': method,
            'Access-Control-Request-Headers': 'content-type'})
        assert result.status_code == 200


def test_integrated_frontend_and_private_files(setup):
    client, _, _ = setup
    assert client.get('/login.html').status_code == 200
    assert client.get('/js/app.js').status_code == 200
    for path in ['/.env', '/schema.sql', '/backend/.env', '/reset-emails/private.eml']:
        assert client.get(path).status_code == 404
