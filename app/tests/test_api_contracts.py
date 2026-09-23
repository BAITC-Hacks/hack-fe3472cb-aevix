"""Exercise the published HTTP surface against a fresh database, never developer data."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings
from app.db import database
from app.db.database import SessionLocal
from app.db.models import ActivityHistory, Employee, Event, Skill
from app.main import app


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


EXPECTED_API = {
    '/health': {'get'},
    **{f'/api/import/{name}': {'post'} for name in ('dataset', 'employees', 'events', 'skills', 'history', 'check-profiles', 'check-history', 'jury-dataset')},
    '/api/employees': {'get'},
    '/api/employees/register': {'post'},
    '/api/employees/{employee_id}': {'get'},
    **{f'/api/employees/{{employee_id}}/{name}': {'get'} for name in ('profile', 'trajectory', 'recommendations')},
    **{f'/api/employees/{{employee_id}}/quests/{{event_id}}/{name}': {'post'} for name in ('select', 'complete')},
    '/api/recommendations/{employee_id}': {'get'},
    **{f'/api/game/{{employee_id}}/{name}': {'get'} for name in ('map', 'progress', 'quests')},
    '/api/teams': {'post'},
    '/api/teams/{team_id}': {'get'},
    **{f'/api/teams/{{team_id}}/{name}': {'post'} for name in ('join', 'pause', 'resume')},
    **{f'/api/teams/{{team_id}}/quests/{{event_id}}/{name}': {'post'} for name in ('start', 'complete')},
    '/api/pairs/invitations': {'get', 'post'},
    '/api/pairs/invitations/{invitation_id}/preview': {'get'},
    '/api/pairs/invitations/{invitation_id}/respond': {'post'},
    '/api/pairs/{pair_id}': {'get'},
    '/api/wallet/{employee_id}': {'get'},
    '/api/esg-goals': {'get'},
    '/api/esg-goals/{goal_id}/contribute': {'post'},
    **{f'/api/hr/{name}': {'get'} for name in ('dashboard', 'skill-gaps', 'inactive-employees', 'events-effectiveness', 'esg-engagement')},
}


def test_every_published_route_is_in_openapi_and_docs_load(client):
    schema = client.get('/openapi.json')
    assert schema.status_code == 200
    paths = schema.json()['paths']
    for path, methods in EXPECTED_API.items():
        assert path in paths, path
        assert methods <= paths[path].keys(), path
    assert client.get('/health').json()['status'] == 'ok'
    for path in ('/docs', '/redoc'):
        response = client.get(path)
        assert response.status_code == 200
        assert 'text/html' in response.headers['content-type']


@pytest.mark.parametrize('route,filename,key', [
    ('employees', 'employees.json', 'employees'), ('check-profiles', 'employees.json', 'employees'),
    ('events', 'events.json', 'events'), ('skills', 'skills.json', 'skills'),
    ('history', 'activity_history.csv', None), ('check-history', 'activity_history.csv', None),
])
def test_each_upload_endpoint_accepts_the_dataset(client, route, filename, key):
    payload = (settings.dataset_path / filename).read_bytes()
    response = client.post(f'/api/import/{route}', files={'file': (filename, payload)})
    assert response.status_code == 200, response.text
    assert response.json()['imported'] > 0
    # Re-upload updates IDs instead of duplicating records.
    again = client.post(f'/api/import/{route}', files={'file': (filename, payload)})
    assert again.json() == response.json()


def test_dataset_and_combined_jury_import_are_atomic_and_idempotent(client):
    assert client.post('/api/import/dataset').status_code == 200
    files = {name: (filename, (settings.dataset_path / filename).read_bytes()) for name, filename in (
        ('employees', 'employees.json'), ('events', 'events.json'), ('skills', 'skills.json'), ('history', 'activity_history.csv'),
    )}
    response = client.post('/api/import/jury-dataset', files=files)
    assert response.status_code == 200, response.text
    assert all(response.json()[key] > 0 for key in files)
    with SessionLocal() as db:
        assert db.query(Employee).count() == 200
        assert db.query(Event).count() == 40
        assert db.query(Skill).count() == 60


@pytest.mark.parametrize('route,filename,payload', [
    ('employees', 'bad.json', b'{'), ('check-profiles', 'bad.json', b'[]'),
    ('events', 'bad.json', b'{"events": [{"event_id": "NEW"}]}'),
    ('skills', 'bad.json', b'{"skills": null}'),
    ('history', 'bad.csv', b'wrong,columns\na,b\n'),
    ('check-history', 'bad.csv', b'record_id,employee_id,event_id,date\nNEW,E0002,EV_005,invalid\n'),
])
def test_invalid_uploads_are_client_errors_and_leave_no_temp_files(client, route, filename, payload):
    before = set(Path('.').glob('tmp_import_*'))
    response = client.post(f'/api/import/{route}', files={'file': (filename, payload)})
    assert response.status_code == 422, response.text
    assert set(Path('.').glob('tmp_import_*')) == before


def test_jury_import_orders_dependencies_and_rolls_back_on_error(client):
    files = {
        'employees': ('employees.json', json.dumps({'employees': [{'employee_id': 'IMPORT_NEW', 'full_name': 'Import Person'}]})),
        'events': ('events.json', json.dumps({'events': [{'event_id': 'IMPORT_EVENT', 'title': 'Import Event'}]})),
        'history': ('history.csv', 'record_id,employee_id,event_id,status\nIMPORT_ROW,IMPORT_NEW,IMPORT_EVENT,completed\n'),
    }
    response = client.post('/api/import/jury-dataset', files=files)
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        assert db.get(ActivityHistory, 'IMPORT_ROW').status == 'completed'
    files['employees'] = ('employees.json', json.dumps({'employees': [{'employee_id': 'IMPORT_ROLLBACK', 'full_name': 'Rollback Person'}]}))
    files['history'] = ('bad.csv', 'record_id,employee_id,event_id\nBAD_ROW,missing,IMPORT_EVENT\n')
    response = client.post('/api/import/jury-dataset', files=files)
    assert response.status_code == 422, response.text
    with SessionLocal() as db:
        assert db.get(Employee, 'IMPORT_ROLLBACK') is None
        assert db.get(ActivityHistory, 'BAD_ROW') is None
    assert client.post('/api/import/jury-dataset').status_code == 422


def test_missing_dataset_file_does_not_apply_earlier_files(client, tmp_path):
    folder = tmp_path / 'partial_dataset'
    folder.mkdir()
    (folder / 'employees.json').write_text(json.dumps({'employees': [{'employee_id': 'ROLLBACK_DIR', 'full_name': 'Rollback'}]}))
    response = client.post('/api/import/dataset', params={'dataset_dir': str(folder)})
    assert response.status_code == 404
    with SessionLocal() as db:
        assert db.get(Employee, 'ROLLBACK_DIR') is None


def test_database_upgrade_preserves_legacy_teams_and_can_run_twice(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'legacy.sqlite'}")
    with engine.begin() as connection:
        connection.execute(text('CREATE TABLE teams (team_id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL, creator_id VARCHAR NOT NULL, max_members INTEGER NOT NULL, status VARCHAR NOT NULL, completed_team_quests INTEGER NOT NULL)'))
        connection.execute(text("INSERT INTO teams VALUES ('legacy', 'Existing team', 'E0002', 5, 'in_progress', 2)"))
    monkeypatch.setattr(database, 'engine', engine)
    database.init_db()
    database.init_db()
    assert {'current_event_id', 'quest_started_at'} <= {column['name'] for column in inspect(engine).get_columns('teams')}
    with engine.connect() as connection:
        row = connection.execute(text("SELECT name, completed_team_quests, current_event_id, status FROM teams WHERE team_id='legacy'")).one()
        assert tuple(row) == ('Existing team', 2, None, 'active')
    engine.dispose()


@pytest.mark.parametrize('path', [
    '/api/employees', '/api/employees/catalog', '/api/employees/E0002',
    '/api/employees/E0002/profile', '/api/employees/E0002/trajectory',
    '/api/employees/E0002/recommendations', '/api/recommendations/E0002',
    '/api/game/E0002/map', '/api/game/E0002/progress', '/api/game/E0002/quests',
])
def test_employee_and_game_http_reads(client, path):
    response = client.get(path)
    assert response.status_code == 200, response.text
    assert response.json() is not None


def test_registered_employee_can_select_and_complete_quest_over_http(client):
    employee = {
        'employee_id': 'HTTP_NEW', 'full_name': 'HTTP New Employee',
        'role': 'Backend Engineer', 'grade': 'Middle',
        'skills': {'SK_PYTHON': 3, 'SK_SYSTEM_DESIGN': 1, 'SK_GIT': 3, 'SK_COMMUNICATION': 2},
        'career_goal': {'target_role': 'Backend Engineer', 'target_grade': 'Senior'},
    }
    registration = client.post('/api/employees/register', json=employee)
    assert registration.status_code == 200, registration.text
    assert registration.json()['updated'] is False
    recommendations = client.get('/api/recommendations/HTTP_NEW').json()['recommendations']
    assert recommendations
    event_id = recommendations[0]['event_id']
    select = client.post(f'/api/employees/HTTP_NEW/quests/{event_id}/select', json={'mode': 'solo'})
    assert select.status_code == 200, select.text
    history = client.get('/api/employees/HTTP_NEW/trajectory').json()
    assert any(row['event_id'] == event_id and row['status'] == 'in_progress' for row in history)
    complete = client.post(f'/api/employees/HTTP_NEW/quests/{event_id}/complete')
    assert complete.status_code == 200, complete.text
    result = complete.json()
    profile = client.get('/api/employees/HTTP_NEW/profile').json()
    assert result['progress_to_next_grade_after'] == profile['progress_to_next_grade']
    assert client.get('/api/wallet/HTTP_NEW').json()['balance'] == result['wallet_balance']
    assert client.post(f'/api/employees/HTTP_NEW/quests/{event_id}/complete').status_code == 409
    assert client.get('/api/game/HTTP_NEW/map').json()['city_progress']['completed_courses'] == 1


@pytest.mark.parametrize('path', [
    '/api/employees/missing', '/api/employees/missing/profile', '/api/employees/missing/trajectory',
    '/api/employees/missing/recommendations', '/api/recommendations/missing',
    '/api/game/missing/map', '/api/game/missing/progress', '/api/game/missing/quests',
])
def test_unknown_employee_is_a_404(client, path):
    assert client.get(path).status_code == 404
