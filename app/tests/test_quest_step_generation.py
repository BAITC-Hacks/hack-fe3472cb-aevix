"""Quest-plan generation validates external output without calling an AI service."""
import json

import pytest

from app.services import llm_service


EVENT = {"event_id": "TEST_QUEST", "title": "System design practice"}
EMPLOYEE = {"employee_id": "E0002", "role": "Backend Engineer"}


def step(number, **overrides):
    return {"step": number, "title": f"Step {number}", "description": "Apply the learning.", "done": False, **overrides}


def mock_response(monkeypatch, raw):
    captured = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(raw).encode()

    def urlopen(req, **_kwargs):
        captured.append(json.loads(req.data))
        return Response()

    monkeypatch.setattr(llm_service.settings, "openai_api_key", "test-key-never-sent")
    monkeypatch.setattr(llm_service.request, "urlopen", urlopen)
    return captured


@pytest.mark.parametrize("parsed", [
    None, [], {}, {"steps": []}, {"steps": [step(1), step(2)]},
    {"steps": [step(number) for number in range(1, 7)]},
    {"steps": [step(1), step(1), step(3)]},
    {"steps": [step(1), step(2), step(4)]},
    {"steps": [step(0), step(2), step(3)]},
    {"steps": [step(True), step(2), step(3)]},
    {"steps": [step(1.0), step(2), step(3)]},
    {"steps": [step("1"), step(2), step(3)]},
    {"steps": [step(1, title=" "), step(2), step(3)]},
    {"steps": [step(1, description=None), step(2), step(3)]},
    {"steps": [step(1, done="false"), step(2), step(3)]},
    {"steps": [None, step(2), step(3)]},
    {"steps": [step(1, coins=1000), step(2), step(3)]},
    {"steps": [step(1), step(2), step(3)], "provider": "untrusted"},
])
def test_malformed_generated_plan_falls_back_without_accepting_progress(monkeypatch, parsed):
    mock_response(monkeypatch, {"output_text": json.dumps(parsed)})
    result = llm_service.generate_quest_steps(EVENT, EMPLOYEE, language="en")
    assert result["provider"] == "template"
    assert result["language"] == "en"
    assert result["steps"][0]["title"] == "Prepare"
    assert [row["step"] for row in result["steps"]] == [1, 2, 3, 4]
    assert all(row["done"] is False for row in result["steps"])


@pytest.mark.parametrize("raw", [
    None, [], {"output": None}, {"output": [None]},
    {"output": [{"content": [None]}]},
    {"output": [{"content": [{"type": "refusal", "refusal": "Unavailable"}]}]},
    {"status": "incomplete", "output_text": json.dumps({"steps": [step(1), step(2), step(3)]})},
    {"error": {"message": "Unavailable"}, "output_text": json.dumps({"steps": [step(1), step(2), step(3)]})},
])
def test_unavailable_or_malformed_model_response_uses_fallback(monkeypatch, raw):
    mock_response(monkeypatch, raw)
    assert llm_service.generate_quest_steps(EVENT, EMPLOYEE)["provider"] == "template"


def test_valid_plan_is_ordered_localized_and_cannot_mark_steps_done(monkeypatch):
    parsed = {"steps": [step(3), step(1, title="  First step  ", done=True), step(2)]}
    captured = mock_response(monkeypatch, {"status": "completed", "output": [{
        "type": "message", "content": [{"type": "output_text", "text": json.dumps(parsed)}],
    }]})
    result = llm_service.generate_quest_steps(EVENT, EMPLOYEE, language="kk")
    assert result["provider"] == "openai"
    assert result["event_id"] == EVENT["event_id"]
    assert result["title"] == EVENT["title"]
    assert result["language"] == "kk"
    assert [row["step"] for row in result["steps"]] == [1, 2, 3]
    assert result["steps"][0]["title"] == "First step"
    assert all(row["done"] is False for row in result["steps"])
    assert "Kazakh" in captured[0]["input"][0]["content"]
    schema = captured[0]["text"]["format"]
    assert schema["strict"] is True
    assert schema["schema"]["properties"]["steps"]["minItems"] == 3
    assert schema["schema"]["properties"]["steps"]["maxItems"] == 5


@pytest.mark.parametrize("language,title", [("ru", "Подготовиться"), ("kk", "Дайындалу"), ("en", "Prepare"), ("unknown", "Подготовиться")])
def test_fallback_plan_supports_each_language_without_network(monkeypatch, language, title):
    monkeypatch.setattr(llm_service.settings, "openai_api_key", None)

    def unexpected_call(*_args, **_kwargs):
        pytest.fail("Fallback plans must not contact an AI service")

    monkeypatch.setattr(llm_service.request, "urlopen", unexpected_call)
    result = llm_service.generate_quest_steps(EVENT, EMPLOYEE, language=language)
    assert result["provider"] == "template"
    assert result["steps"][0]["title"] == title


def test_model_transport_error_uses_localized_fallback(monkeypatch):
    monkeypatch.setattr(llm_service.settings, "openai_api_key", "test-key-never-sent")

    def unavailable(*_args, **_kwargs):
        raise OSError("Simulated network failure")

    monkeypatch.setattr(llm_service.request, "urlopen", unavailable)
    result = llm_service.generate_quest_steps(EVENT, EMPLOYEE, language="en")
    assert result["provider"] == "template"
    assert result["steps"][0]["title"] == "Prepare"
