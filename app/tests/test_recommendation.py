from app.db.database import init_db
from app.services.import_service import seed_demo_data
from app.services.recommendation_service import get_employee_recommendations


def test_recommendation_service_targets_grade_gap():
    init_db()
    seed_demo_data()
    result = get_employee_recommendations("E0002")

    assert result["employee_id"] == "E0002"
    assert result["target_grade"] == "Senior"
    assert result["progress_to_next_grade"] >= 0
    assert len(result["recommendations"]) >= 1
    assert result["recommendations"][0]["score"] > 0
