"""Provision employee passwords locally; plaintext never enters the application DB."""
import argparse
import csv
import os
from pathlib import Path
import secrets
import tempfile

from sqlalchemy import delete, select

from app.core.config import settings
from app.db.auth_models import AuthSession, EmployeeAccount
from app.db.database import SessionLocal, init_db
from app.db.models import Employee
from app.services.auth_service import hash_password

FIELDS = ["employee_id", "full_name", "username", "password"]


def provision(employee_ids: list[str] | None = None, *, rotate: bool = False, output: Path | None = None) -> dict:
    output = output or Path(__file__).resolve().parents[1] / ".local" / "employee-access.csv"
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    pending_exports = list(output.parent.glob(f".{output.name}.*.pending"))
    if pending_exports:
        raise RuntimeError(f"An unfinished credentials export needs recovery before provisioning: {pending_exports[0]}. Preserve this private file and restore it to {output} after checking the previous command result.")
    existing_rows = {}
    if output.exists():
        with output.open(newline="") as handle:
            existing_rows = {row["employee_id"]: row for row in csv.DictReader(handle)}
    pending_path = None
    created = 0
    reset = 0
    with SessionLocal() as db:
        employees = db.scalars(select(Employee).order_by(Employee.employee_id)).all()
        if employee_ids:
            wanted = set(employee_ids)
            missing = wanted - {employee.employee_id for employee in employees}
            if missing:
                raise ValueError("Unknown employee IDs: " + ", ".join(sorted(missing)))
            employees = [employee for employee in employees if employee.employee_id in wanted]
        if any(employee.employee_id == settings.hr_username for employee in employees):
            raise ValueError("An employee ID conflicts with the reserved HR username")
        for employee in employees:
            account = db.get(EmployeeAccount, employee.employee_id)
            if account is not None and not rotate:
                continue
            password = secrets.token_urlsafe(24)
            password_hash = hash_password(password)
            if account is None:
                account = EmployeeAccount(employee_id=employee.employee_id, username=employee.employee_id, password_hash=password_hash, active=True)
                db.add(account)
                created += 1
            else:
                account.password_hash = password_hash
                account.active = True
                db.execute(delete(AuthSession).where(AuthSession.employee_id == employee.employee_id))
                reset += 1
            existing_rows[employee.employee_id] = {"employee_id": employee.employee_id, "full_name": employee.full_name, "username": account.username, "password": password}
        if created or reset:
            # Prepare the private file before committing; a failed DB commit leaves
            # neither new accounts nor a replacement of the existing access file.
            fd, pending_path = tempfile.mkstemp(prefix=f".{output.name}.", suffix=".pending", dir=output.parent)
            try:
                with os.fdopen(fd, "w", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=FIELDS)
                    writer.writeheader()
                    writer.writerows(existing_rows[key] for key in sorted(existing_rows))
                    handle.flush()
                    os.fsync(handle.fileno())
                db.commit()
            except Exception:
                db.rollback()
                Path(pending_path).unlink(missing_ok=True)
                raise
            try:
                os.replace(pending_path, output)
            except OSError as exc:
                raise RuntimeError(f"Accounts saved. Credentials remain in the private recovery file {pending_path}; move it to {output} before rerunning provisioning.") from exc
            os.chmod(output, 0o600)
    return {"created": created, "reset": reset, "file": str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Create local employee accounts for the shared Career City platform")
    parser.add_argument("--employee-id", action="append", help="Provision only this employee; may be repeated")
    parser.add_argument("--rotate", action="store_true", help="Replace selected existing passwords and revoke their sessions")
    args = parser.parse_args()
    init_db()
    result = provision(args.employee_id, rotate=args.rotate)
    print(f"Employee accounts created: {result['created']}; passwords reset: {result['reset']}.")
    if result["created"] or result["reset"]:
        print(f"Private credentials file: {result['file']}")
    print("Shared sign-in: http://localhost:5173/")


if __name__ == "__main__":
    main()
