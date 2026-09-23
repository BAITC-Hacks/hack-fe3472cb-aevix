from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.services.import_service import (
    import_dataset_from_path, import_employees, import_events,
    import_history, import_skills, import_transaction,
)

router = APIRouter()


def _import_optional(file: UploadFile | None, importer, suffix: str, db: Session | None = None) -> int:
    if file is None:
        return 0
    if not file.filename:
        raise HTTPException(status_code=400, detail="File name is required")
    # Each request has its own file; all paths are removed, including on failure.
    with NamedTemporaryFile(suffix=suffix) as handle:
        handle.write(file.file.read())
        handle.flush()
        return importer(Path(handle.name), db)


@router.post("/dataset")
def import_dataset(dataset_dir: str | None = None) -> dict[str, Any]:
    return import_dataset_from_path(dataset_dir)


@router.post("/check-profiles")
@router.post("/employees")
def import_employee_file(file: UploadFile = File(...)) -> dict[str, Any]:
    return {"status": "ok", "imported": _import_optional(file, import_employees, ".json")}


@router.post("/check-history")
@router.post("/history")
def import_history_file(file: UploadFile = File(...)) -> dict[str, Any]:
    return {"status": "ok", "imported": _import_optional(file, import_history, ".csv")}


@router.post("/events")
def import_event_file(file: UploadFile = File(...)) -> dict[str, Any]:
    return {"status": "ok", "imported": _import_optional(file, import_events, ".json")}


@router.post("/skills")
def import_skill_file(file: UploadFile = File(...)) -> dict[str, Any]:
    return {"status": "ok", "imported": _import_optional(file, import_skills, ".json")}


@router.post("/jury-dataset")
def import_jury_dataset(
    employees: UploadFile | None = File(None),
    history: UploadFile | None = File(None),
    events: UploadFile | None = File(None),
    skills: UploadFile | None = File(None),
) -> dict[str, Any]:
    if all(file is None for file in (employees, history, events, skills)):
        raise HTTPException(status_code=422, detail="Upload at least one dataset file")
    with import_transaction() as db:
        return {
            "status": "ok",
            "employees": _import_optional(employees, import_employees, ".json", db),
            "events": _import_optional(events, import_events, ".json", db),
            "skills": _import_optional(skills, import_skills, ".json", db),
            "history": _import_optional(history, import_history, ".csv", db),
        }
