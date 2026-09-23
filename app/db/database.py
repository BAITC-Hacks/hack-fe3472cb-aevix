from typing import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    from app.db.models import ActivityHistory, Employee, Event, RoleProfile, Skill

    Base.metadata.create_all(bind=engine)
    # create_all creates new tables but does not add columns to an existing DB.
    columns = {column["name"] for column in inspect(engine).get_columns("teams")}
    with engine.begin() as connection:
        if "current_event_id" not in columns:
            connection.execute(text("ALTER TABLE teams ADD COLUMN current_event_id VARCHAR REFERENCES events(event_id)"))
            # The old backend did not persist which quest was started.
            connection.execute(text("UPDATE teams SET status='active' WHERE status='in_progress'"))
        if "quest_started_at" not in columns:
            connection.execute(text("ALTER TABLE teams ADD COLUMN quest_started_at DATE"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
