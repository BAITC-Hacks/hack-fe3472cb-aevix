"""Workspace contract checks; conftest.py supplies a fresh temporary database."""
import pytest
from fastapi import HTTPException
from app.db.database import SessionLocal, init_db
from app.db.models import ActivityHistory, Employee
from app.routers.employee_router import catalog
from app.services.import_service import seed_demo_data
from app.services.recommendation_service import get_employee_profile, get_employee_recommendations, get_employee_trajectory, complete_quest
from app.services.progress_service import compute_progress_to_next_grade
from app.services.game_service import get_game_map
from app.utils.grade import grade_index, get_role_target


def test_workspace_consistency():
    init_db()
    seed_demo_data()
    employee_id = 'E0002'
    profile = get_employee_profile(employee_id)
    recommendations = get_employee_recommendations(employee_id)
    city = get_game_map(employee_id)
    with SessionLocal() as db:
        progress = compute_progress_to_next_grade(db.get(Employee, employee_id))
    assert profile['progress_to_next_grade'] == recommendations['progress_to_next_grade'] == city['progress_to_next_grade'] == progress
    assert city['career_level'] == grade_index(profile['grade']) + 1
    assert city['center']['level'] == city['career_level']
    assert city['center']['progress_to_next_grade'] == progress
    assert city['recommended_quest_ids'] == [q['event_id'] for q in recommendations['recommendations']]
    data = catalog()
    assert any(p['role'] == profile['target_role'] and p['grade'] == profile['target_grade'] for p in data['role_profiles'])
    event_id = recommendations['recommendations'][0]['event_id']
    assert any(e['event_id'] == event_id for e in data['events'])
    with SessionLocal() as db:
        db.add(ActivityHistory(record_id='test_active', employee_id=employee_id, event_id=event_id, status='in_progress', completion_pct=25))
        db.commit()
    result = complete_quest(employee_id, event_id)
    after = get_employee_profile(employee_id)
    assert result['progress_to_next_grade_after'] == after['progress_to_next_grade'] == get_game_map(employee_id)['progress_to_next_grade']
    assert result['progress_to_next_grade_after'] >= result['progress_to_next_grade_before']
    assert all(q['event_id'] != event_id for q in get_employee_recommendations(employee_id)['recommendations'])
    history = [h for h in get_employee_trajectory(employee_id) if h['event_id'] == event_id]
    assert not any(h['status'] == 'in_progress' for h in history)
    assert any(h['status'] == 'completed' and h['completion_pct'] == 100 for h in history)
    # EV_036 — регулярный клуб, по правилам датасета его можно проходить повторно
    if event_id != 'EV_036':
        with pytest.raises(HTTPException) as error:
            complete_quest(employee_id, event_id)
        assert error.value.status_code == 409
        assert get_employee_profile(employee_id)['skills'] == after['skills']


def test_target_and_missing_employee():
    assert get_role_target({'role': 'Engineer', 'grade': 'Junior', 'career_goal': {'target_grade': 'Lead'}}) == ('Engineer', 'Lead')
    with pytest.raises(HTTPException) as error:
        get_game_map('missing-employee')
    assert error.value.status_code == 404


def test_hr_uses_actual_learning_history():
    from app.services.hr_service import get_hr_dashboard
    with SessionLocal() as db:
        rows = db.query(ActivityHistory).all()
        expected = round(sum(row.status == 'completed' for row in rows) / len(rows), 2)
    assert get_hr_dashboard()['events_completion_rate'] == expected
