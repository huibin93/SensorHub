from typing import Generator
from sqlmodel import Session
from app.core.database import get_session

# Re-export get_session as dependency
def get_db() -> Generator[Session, None, None]:
    yield from get_session()
