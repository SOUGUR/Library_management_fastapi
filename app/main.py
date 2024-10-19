from fastapi import FastAPI, Depends, HTTPException, APIRouter, Response
from sqlalchemy.orm import Session
from .database import get_db, Base, engine
from .schemas import UserCreate, BookCreate, UserLogin, UserRead
from .models import User, Book, BorrowingRecord
from passlib.context import CryptContext
from .auth import verify_token, create_access_token, get_token_from_cookie
from typing import List


Base.metadata.create_all(bind=engine)

app = FastAPI()
router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

"""@app.post("/signup")
async def signup(user: UserCreate, db: Session = Depends(get_db)):
    # Check if the username already exists
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    # Hash the password
    hashed_password = get_password_hash(user.password)

    # Determine the user's role based on librarian request
    if user.librarian_request:
        new_user = User(
            username=user.username,
            password=hashed_password,
            role="PENDING LIBRARIAN",
            approved=False
        )
    else:
        new_user = User(
            username=user.username,
            password=hashed_password,
            role="MEMBER",
            approved=True
        )

    # Add the new user to the database
    db.add(new_user)
    db.commit()
    
    return {"message": "User created successfully, librarian approval pending if requested"}"""

"""@app.post("/login")
async def login(user: UserLogin, response: Response, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == user.username).first()

    # Check if user exists and verify the password
    if not db_user or not db_user.verify_password(user.password):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    # Include role in the JWT token
    access_token = create_access_token(data={"sub": db_user.username, "role": db_user.role})

    # Set the access token as an HttpOnly cookie
    response.set_cookie(key="access_token", value=access_token, httponly=True)

    return {"message": "Login successful", "token_type": "bearer"}"""

def get_current_user(token: str = Depends(get_token_from_cookie), db: Session = Depends(get_db)):
    user_data = verify_token(token)  # Verify the token and get user info
    user = db.query(User).filter(User.username == user_data["username"]).first()  # Get the full user object from DB

    # Check if the user exists and has one of the allowed roles
    if not user or user.role not in ["MEMBER", "LIBRARIAN", "SUPERUSER", "PENDING_LIBRARIAN"]:
        raise HTTPException(status_code=403, detail="User does not exist or has insufficient permissions")
    
    return user  


def get_current_librarian_or_superuser(token: str = Depends(get_token_from_cookie)):
    user_data = verify_token(token)
    if user_data["role"] not in ["LIBRARIAN", "SUPERUSER"]:
        raise HTTPException(status_code=403, detail="Permission denied")
    return user_data["username"]

#@router.put("/approve-librarian/{user_id}", dependencies=[Depends(get_current_librarian_or_superuser)])
def approve_librarian(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.role != "PENDING_LIBRARIAN":
        raise HTTPException(status_code=400, detail="User is not a pending librarian")

    # Promote user to librarian
    user.role = "LIBRARIAN"
    db.commit()

    return {"message": f"User {user.username} has been approved as a librarian"}


#@router.post("/books/")
def add_book(book: BookCreate, db: Session = Depends(get_db), current_user: str = Depends(get_current_librarian_or_superuser)):
    new_book = Book(
        title=book.title,
        author=book.author,
        total_copies=book.total_copies,
        available_copies=book.total_copies,
    )
    db.add(new_book)
    db.commit()
    
    return {"message": "Book added successfully"}

@router.delete("/books/{book_id}")
def remove_book(
    book_id: int, 
    db: Session = Depends(get_db), 
    current_user: str = Depends(get_current_librarian_or_superuser)
):
    book = db.query(Book).filter(Book.id == book_id).first()
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    db.delete(book)
    db.commit()
    return {"message": "Book removed successfully"}



#@app.put("/books/borrow/{book_id}")
def borrow_book(book_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # The current_user object contains the full user object
    book = db.query(Book).filter(Book.id == book_id).first()
    
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    if book.available_copies <= 0:
        raise HTTPException(status_code=400, detail="No copies available to borrow")

    # Check if the user has already borrowed this book
    existing_record = db.query(BorrowingRecord).filter(
        BorrowingRecord.book_id == book_id,
        BorrowingRecord.user_id == current_user.id,
        BorrowingRecord.status == "BORROWED"
    ).first()

    if existing_record:
        raise HTTPException(status_code=400, detail="You have already borrowed this book")

    # Create a new borrowing record
    borrowing_record = BorrowingRecord(user_id=current_user.id, book_id=book_id, status="BORROWED")
    
    db.add(borrowing_record)
    book.available_copies -= 1
    
    db.commit()
    
    return {"message": f"{current_user.username} borrowed {book.title} successfully"}


#@app.put("/books/return/{book_id}")
def return_book(book_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if the user has borrowed this book
    record = db.query(BorrowingRecord).filter(
        BorrowingRecord.book_id == book_id,
        BorrowingRecord.user_id == current_user.id,
        BorrowingRecord.status == "BORROWED"
    ).first()
    
    if not record:
        raise HTTPException(status_code=404, detail="No borrowing record found for this book")

    # Update the status to RETURNED
    record.status = "RETURNED"
    
    # Increment available copies by 1
    book = db.query(Book).filter(Book.id == book_id).first()
    
    if book:
        book.available_copies += 1
    
    db.commit()
    
    return {"message": f"{current_user.username} returned {book.title} successfully"}




#@app.get("/librarians/pending", response_model=List[UserCreate])  
def list_pending_librarians(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Check if the current user is a librarian or superuser
    if current_user.role not in ["LIBRARIAN", "SUPERUSER"]:
        raise HTTPException(status_code=403, detail="Permission denied")

    # Query for users with role PENDING_LIBRARIAN
    pending_librarians = db.query(User).filter(User.role == "PENDING_LIBRARIAN").all()

    return pending_librarians

#@router.get("/books/available", response_model=List[BookCreate])  # Use your Book response model
def list_available_books(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    available_books = db.query(Book).filter(Book.available_copies > 0).all()
    return available_books

#@router.get("/admin/users", response_model=List[UserRead])
def list_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role in ["MEMBER", "PENDING_LIBRARIAN", "LIBRARIAN"]:
        raise HTTPException(status_code=403, detail="Permission denied, you are not a Admin")
    users = db.query(User).all()
    
    return users

@router.delete("/admin/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Ensure the current user is a superuser
    if current_user.role != "SUPERUSER":
        raise HTTPException(status_code=403, detail="Permission denied")

    # Find the user by their id
    user_record = db.query(User).filter(User.id == user_id).first()
    
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent a superuser from deleting themselves
    if user_record.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    
    db.delete(user_record)
    db.commit()

    return {"message": f"User {user_record.username} deleted successfully"}

#@app.delete("/users/delete")
def delete_account(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    user_record = db.query(User).filter(User.id == current_user.id).first()
    
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user_record)
    db.commit()
    
    return {"message": f"Account for {current_user.username} has been deleted successfully"}


"""@app.get("/logout")
def logout(response: Response):
    # Instruct the browser to delete the 'access_token' cookie
    response.delete_cookie(key="access_token", path="/")  # Add 'domain' if necessary
    
    return {"message": "Logout successful. Access token deleted."}

app.include_router(router)"""
