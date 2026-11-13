"""MySQL connection and one database session per request."""
import os

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from . import config  # Loads backend/.env before reading the database settings.

url = URL.create(
    'mysql+pymysql',
    username=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    host=os.getenv('DB_HOST', '127.0.0.1'),
    port=int(os.getenv('DB_PORT', '3306')),
    database=os.getenv('DB_NAME', 'todo_manager'),
    query={'charset': 'utf8mb4'},
)
engine = create_engine(url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    with SessionLocal() as db:
        yield db
