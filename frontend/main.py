from fastapi import FastAPI, Depends, HTTPException, Request, Response, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Book
from passlib.context import CryptContext
from app.auth import create_access_token
from app.main import borrow_book, get_current_user, return_book, delete_user, list_available_books, add_book, list_pending_librarians, get_current_librarian_or_superuser, approve_librarian, list_users
from app.schemas import BookCreate

frontapp = FastAPI()

# Jinja2 template setup
templates = Jinja2Templates(directory="templates")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

@frontapp.get("/signup", response_class=HTMLResponse)
async def get_signup_form(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@frontapp.post("/signup")
async def signup(
    request: Request,  
    username: str = Form(...),
    password: str = Form(...),
    librarian_request: bool = Form(False),
    db: Session = Depends(get_db)
):
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed_password = get_password_hash(password)

    new_user = User(
        username=username,
        password=hashed_password,
        role="PENDING LIBRARIAN" if librarian_request else "MEMBER",
        approved=not librarian_request
    )

    db.add(new_user)
    db.commit()
    # Render success.html after user creation
    return templates.TemplateResponse("success.html", {"request": request, "message": "User created successfully, librarian approval pending if requested"})

@frontapp.get("/login", response_class=HTMLResponse)
async def get_login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@frontapp.post("/login")
async def login(
    request: Request,  
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    db_user = db.query(User).filter(User.username == username).first()

    if not db_user or not db_user.verify_password(password):
        raise HTTPException(status_code=400, detail="Invalid username or password")

    access_token = create_access_token(data={"sub": db_user.username, "role": db_user.role})
    
    # Setting the cookie
    response.set_cookie(key="access_token", value=access_token, path="/")

    # Manually returning the response with cookies set
    return templates.TemplateResponse(
        "success.html",
        {"request": request, "message": "Login successful!"},
        headers=response.headers  # Pass response headers to ensure the cookie is set
    )
@frontapp.get("/submit_borrow_book", response_class=HTMLResponse)
async def get_borrow_book_form(request: Request):
    return templates.TemplateResponse("borrow_book.html", {"request": request})

@frontapp.post("/submit_borrow_book")
async def submit_borrow_book(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    form = await request.form()
    book_id = form.get("book_id")
    response = borrow_book(int(book_id), db, current_user)

    return templates.TemplateResponse("success.html", {"request": request, "message": response["message"]})

@frontapp.get("/submit_return_book", response_class=HTMLResponse)
async def get_return_book_form(request: Request):
    return templates.TemplateResponse("return_book.html", {"request": request})

@frontapp.post("/submit_return_book")
async def submit_return_book(
    request: Request, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    form = await request.form()
    book_id = form.get("book_id")
    
    # Call the return_book function
    response = return_book(int(book_id), db, current_user)

    return templates.TemplateResponse("success.html", {"request": request, "message": response["message"]})


@frontapp.get("/available_books", response_class=HTMLResponse)
async def available_books(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
      # Use get_current_user here
    books = db.query(Book).all()
    
    return templates.TemplateResponse("available_books.html", {
        "request": request, 
        "books": books,
        "current_user": current_user  # Pass current_user to the template
    })

@frontapp.delete("/books/{book_id}")
def remove_book(
    book_id: int, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in ["LIBRARIAN", "SUPERUSER"]:
        raise HTTPException(status_code=403, detail="Permission denied!")

    book = db.query(Book).filter(Book.id == book_id).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    db.delete(book)
    db.commit()
    
    return JSONResponse(content={"message": "Book removed successfully"}, status_code=200)

@frontapp.get("/add_book", response_class=HTMLResponse)
async def get_add_book_form(request: Request, current_user: str = Depends(get_current_librarian_or_superuser)):
    return templates.TemplateResponse("add_book.html", {"request": request})

@frontapp.post("/add_book", response_class=HTMLResponse)
async def submit_add_book(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    
    # Create a BookCreate object from form data
    book_data = BookCreate(
        title=form.get("title"),
        author=form.get("author"),
        total_copies=int(form.get("total_copies"))
    )
    
    # Call the add_book function
    message = add_book(book_data, db)

    return templates.TemplateResponse("success.html", {"request": request, "message": message["message"]})

@frontapp.get("/librarians/pending", response_class=HTMLResponse)
async def show_pending_librarians(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    pending_librarians = list_pending_librarians(db=db, current_user=current_user)
    return templates.TemplateResponse("pending_librarians.html", {"request": request, "librarians": pending_librarians})

@frontapp.post("/librarians/approve")
async def approve_librarian_handler(
    request: Request,
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    current_username: str = Depends(get_current_librarian_or_superuser)  # Now it returns the username
):
    current_user = db.query(User).filter(User.username == current_username).first()

    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Approve the librarian using the existing function
    approve_librarian(user_id=user_id, db=db)
    pending_librarians = list_pending_librarians(db=db, current_user=current_user)
    return templates.TemplateResponse("pending_librarians.html", {"request": request, "librarians": pending_librarians, "message": "Librarian approved successfully"})

# Function to get userlist by admin
@frontapp.get("/admin/users", response_class=HTMLResponse)
async def show_users(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = list_users(db=db, current_user=current_user)
    # Render the page with the list of users
    return templates.TemplateResponse("users_list.html", {"request": request, "users": users})

# Function to handle user deletion by admin
@frontapp.post("/admin/delete_user")
async def delete_user_handler(
    request: Request,
    user_id: int = Form(...),
    db: Session = Depends(get_db),
    current_username: str = Depends(get_current_user)
):
    current_user = db.query(User).filter(User.username == current_username.username).first()

    # Reuse the existing `delete_user` function to delete the selected user
    delete_user(user_id=user_id, db=db, current_user=current_user)

    # Fetch the updated list of users after deletion
    users = list_users(db=db, current_user=current_user)

    # Render the page again with the updated list of users
    return templates.TemplateResponse("users_list.html", {"request": request, "users": users, "message": "User deleted successfully"})


@frontapp.get("/perform_logout", response_class=HTMLResponse)
async def perform_logout(request: Request, response: Response):  
    response.delete_cookie(key="access_token", path="/")
    return templates.TemplateResponse("success.html", {"request": request, "message": "Logout successful. Access token deleted."})

@frontapp.post("/users/delete")
async def delete_account(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    print(f"User {current_user.username} is attempting to delete their account.")
    user_record = db.query(User).filter(User.id == current_user.id).first()
    
    if not user_record:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user_record)
    db.commit()

    return templates.TemplateResponse("success.html", {
        "request": request,
        "message": f"Account for {current_user.username} has been deleted successfully."
    })