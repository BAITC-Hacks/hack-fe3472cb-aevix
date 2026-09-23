"""Create local HR credentials without writing plaintext secrets to tracked files."""
import argparse
import os
from pathlib import Path
import secrets

from app.core.config import settings
from app.services.auth_service import hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description="Configure local HR sign-in")
    parser.add_argument("--rotate", action="store_true", help="Replace the HR password and revoke existing sessions")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    access_file = root / ".local" / "hr-access.txt"
    if settings.hr_password_hash and not args.rotate:
        print("HR sign-in is already configured. Use --rotate to replace the password.")
        return
    password = secrets.token_urlsafe(24)
    password_hash = hash_password(password)
    env_file = root / ".env"
    contents = env_file.read_text() if env_file.exists() else ""
    # Preserve all unrelated settings; never output the existing environment.
    lines = [line for line in contents.splitlines() if line.split("=", 1)[0].strip() not in {"HR_USERNAME", "HR_PASSWORD_HASH"}]
    lines.extend([f"HR_USERNAME={settings.hr_username}", f"HR_PASSWORD_HASH='{password_hash}'"])
    fd = os.open(env_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write("\n".join(lines) + "\n")
    os.chmod(env_file, 0o600)
    access_file.parent.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(access_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as handle:
        handle.write(f"Career City: http://localhost:5173/\nUsername: {settings.hr_username}\nPassword: {password}\n\nHR account: employee preview and HR analytics in the shared menu.\nLocal credentials. Do not commit or share this file.\n")
    os.chmod(access_file, 0o600)
    if args.rotate:
        from app.db.database import init_db, SessionLocal
        from app.db.auth_models import HrSession
        init_db()
        with SessionLocal() as db:
            db.query(HrSession).filter_by(role="hr").delete()
            db.commit()
    print(f"HR credentials saved locally: {access_file}")
    print("Restart the backend to apply the configuration.")


if __name__ == "__main__":
    main()
