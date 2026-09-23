from __future__ import annotations

import json
from typing import Any
from urllib import error, request

from app.core.config import settings


def _template_explanations(candidates: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "event_id": item["event_id"],
            "explanation": item.get("explanation", "This event addresses a verified skill gap for the target grade."),
            "employee_friendly_reason": item.get("reason", item.get("explanation", "This is a relevant next step.")),
            "risk_note": "Review prerequisites and availability before starting.",
            "expected_outcome": "The affected skill gap should decrease after successful completion.",
        }
        for item in candidates
    ]


def explain_recommendations(context: dict[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    fallback = {
        "summary": "Recommendations were calculated by the deterministic Career Quest engine.",
        "recommendation_explanations": _template_explanations(candidates),
        "provider": "template",
    }
    api_key = settings.openai_api_key
    if not api_key or not candidates:
        return fallback

    payload = {
        "model": settings.openai_model,
        "input": [
            {
                "role": "system",
                "content": "Explain only the deterministic recommendation factors supplied by the backend. Do not select, reorder, or invent events. Return valid JSON.",
            },
            {
                "role": "user",
                "content": json.dumps({"context": context, "candidates": candidates}, ensure_ascii=False),
            },
        ],
        "text": {
            "format": {
                "type": "json_schema",
                "name": "career_quest_explanation",
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "summary": {"type": "string"},
                        "recommendation_explanations": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "event_id": {"type": "string"},
                                    "explanation": {"type": "string"},
                                    "employee_friendly_reason": {"type": "string"},
                                    "risk_note": {"type": "string"},
                                    "expected_outcome": {"type": "string"},
                                },
                                "required": ["event_id", "explanation", "employee_friendly_reason", "risk_note", "expected_outcome"],
                            },
                        },
                    },
                    "required": ["summary", "recommendation_explanations"],
                },
            },
        },
    }
    try:
        http_request = request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(http_request, timeout=12) as response:
            raw = json.loads(response.read().decode("utf-8"))
        output_text = raw.get("output_text")
        if not output_text:
            for item in raw.get("output", []):
                for content in item.get("content", []):
                    if content.get("text"):
                        output_text = content["text"]
                        break
        parsed = json.loads(output_text or "{}")
        if not isinstance(parsed.get("recommendation_explanations"), list):
            return fallback
        return {**fallback, **parsed, "provider": "openai"}
    except (OSError, ValueError, KeyError, TypeError, error.URLError):
        return fallback
