from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.services.import_service import import_dataset_from_path, import_employees, import_events, import_history, import_skills

router = APIRouter()


@router.post("/dataset")
def import_dataset(dataset_dir: str | None = None) -> dict[str, Any]:
    return import_dataset_from_path(dataset_dir)


@router.post("/employees")
def import_employee_file(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")
    try:
        raw = file.file.read()
        payload = raw.decode("utf-8")
        import json
        from pathlib import Path
        path = Path("./tmp_import_employees.json")
        path.write_text(payload, encoding="utf-8")
        count = import_employees(path)
        path.unlink(missing_ok=True)
        return {"status": "ok", "imported": count}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/events")
def import_event_file(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")
    try:
        import json
        from pathlib import Path
        raw = file.file.read().decode("utf-8")
        path = Path("./tmp_import_events.json")
        path.write_text(raw, encoding="utf-8")
        count = import_events(path)
        path.unlink(missing_ok=True)
        return {"status": "ok", "imported": count}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/skills")
def import_skill_file(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")
    try:
        import json
        from pathlib import Path
        raw = file.file.read().decode("utf-8")
        path = Path("./tmp_import_skills.json")
        path.write_text(raw, encoding="utf-8")
        count = import_skills(path)
        path.unlink(missing_ok=True)
        return {"status": "ok", "imported": count}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/history")
def import_history_file(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")
    try:
        from pathlib import Path
        raw = file.file.read()
        path = Path("./tmp_import_history.csv")
        path.write_bytes(raw)
        count = import_history(path)
        path.unlink(missing_ok=True)
        return {"status": "ok", "imported": count}
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(exc)) from exc
