"""Keep every backend test isolated from the developer's working database."""
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import database
from app.core.config import settings
from app.services import hr_service  # Load its SessionLocal before patching aliases.
from app.services.import_service import seed_demo_data


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "openai_api_key", None)
    engine = create_engine(f"sqlite:///{tmp_path / 'workspace.sqlite'}")
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(database, "engine", engine)
    for name, module in list(sys.modules.items()):
        if (name.startswith("app.") or name.startswith("test_")) and hasattr(module, "SessionLocal"):
            monkeypatch.setattr(module, "SessionLocal", factory)
    database.init_db()
    seed_demo_data()
    yield
    engine.dispose()
