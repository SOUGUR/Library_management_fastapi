from sqlalchemy.orm import sessionmaker
from app.database import engine, Base
from app.models import User
from passlib.context import CryptContext

# Create a session to interact with the database
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Initialize password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Helper function to hash password
def get_password_hash(password):
    return pwd_context.hash(password)

# Create a superuser manually
def create_superuser(username: str, password: str, role: str):
    hashed_password = get_password_hash(password)
    new_superuser = User(
        username=username,
        password=hashed_password,
        role=role,  # Use 'SUPERUSER' or 'LIBRARIAN'
        approved=True  # Automatically approve the superuser/librarian
    )
    
    db.add(new_superuser)
    db.commit()
    print(f"Created {role}: {username}")

# Call the function to create the superuser
if __name__ == "__main__":
    create_superuser("admin", "adminpassword123", "SUPERUSER")  # Example for SUPERUSER

    # Close the session
    db.close()


