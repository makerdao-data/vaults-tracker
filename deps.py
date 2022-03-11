from typing import Generator
from sqlalchemy.orm import Session
from database import SessionLocal, engine


def get_db() -> Generator[Session, None, None]:
    try:
        db = SessionLocal(bind=engine)
        yield db
    finally:
        db.close()
        close_engine()

def close_engine() -> None:
    engine.dispose()