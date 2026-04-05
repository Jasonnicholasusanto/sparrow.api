from collections.abc import Generator
from sqlmodel import Session, create_engine
from supabase import Client, create_client
from app.core.config import settings


engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


def get_db() -> Generator[Session, None]:
    # This is a standard FastAPI dependency.
    # It opens a SQLAlchemy/SQLModel session to the Supabase database and automatically closes it after the request finishes.
    with Session(engine) as session:
        yield session


supabase_client: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY,
)
