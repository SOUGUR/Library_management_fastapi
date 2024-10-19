from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str
    librarian_request: bool = False  # Default is False

    class Config:
        schema_extra = {
            "example": {
                "username": "john_doe",
                "password": "strongpassword123",
                "librarian_request": True  # True if the user requests to be a librarian
            }
        }
        

class BookCreate(BaseModel):
    title: str
    author: str
    total_copies: int  # Number of copies to add

class BorrowingRecordCreate(BaseModel):
    user_id: int
    book_id: int

class UserLogin(BaseModel):
    username: str
    password: str

class UserRead(BaseModel):
    id: int
    username: str
    role: str
    approved: bool

    class Config:
        orm_mode = True