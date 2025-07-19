# file: database.py

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# --- Change these details for your PostgreSQL database ---
DATABASE_URL = "postgresql://postgres:postgres@localhost/walkout_store_db"
# Example: "postgresql://postgres:mysecretpassword@localhost/walkout_store_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency to get a DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

