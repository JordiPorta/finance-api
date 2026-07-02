from sqlmodel import SQLModel, Session, create_engine

from config import settings

# SQLite needs check_same_thread disabled for use with FastAPI's threadpool.
connect_args = (
    {"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {}
)

engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    """Create all tables. Import models so they register with SQLModel.metadata."""
    import models  # noqa: F401  (ensures model modules are imported)

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
