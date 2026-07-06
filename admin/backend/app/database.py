import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

SQLITE_PATH = os.getenv("SQLITE_PATH", "data/fay.db")
Path(SQLITE_PATH).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    f"sqlite:///{SQLITE_PATH}", connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()
