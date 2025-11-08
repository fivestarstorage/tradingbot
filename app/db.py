import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# SQLite file in project root by default
DB_PATH = os.getenv('TRADINGBOT_DB_PATH', os.path.join(os.path.dirname(__file__), '..', 'tradingbot.db'))
DB_URL = f"sqlite:///{os.path.abspath(DB_PATH)}"

engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False},
    pool_size=20,  # Increase from default 5
    max_overflow=40,  # Increase from default 10
    pool_timeout=60,  # Increase timeout to 60s
    pool_recycle=3600,  # Recycle connections after 1 hour
    pool_pre_ping=True  # Verify connections before using
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


