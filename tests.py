from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# SQLAlchemy Setup
DATABASE_URL = "postgresql://postgres:dispatchingisprofitable@/dispatcher-bot-db?host=/var/run/postgresql"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_db_connection():
    try:
        # Try to create a session and execute a simple query
        db = SessionLocal()
        # Test query - this will fail if connection is bad
        db.execute(text("SELECT 1"))
        print("Database connection successful!")
        db.close()
        return True
    except Exception as e:
        print(f"Database connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    test_db_connection()