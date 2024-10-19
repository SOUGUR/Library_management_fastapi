from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Ensure the database URL is correctly formatted
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:Iamsourabh#123@localhost/library_db"

# Create a new SQLAlchemy engine
engine = create_engine(SQLALCHEMY_DATABASE_URL)  # Removed connect_args for MySQL

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a base class for your models
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
