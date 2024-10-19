from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from .database import Base
from passlib.context import CryptContext


Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)  
    password = Column(String(100))  
    role = Column(String(20), default="MEMBER")  
    approved = Column(Boolean, default=False)  

    def set_password(self, plain_password):
        self.password = pwd_context.hash(plain_password)

    def verify_password(self, plain_password):
        return pwd_context.verify(plain_password, self.password)

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    author = Column(String)
    total_copies = Column(Integer)  # Total number of copies
    available_copies = Column(Integer)  # Number of available copies

class BorrowingRecord(Base):
    __tablename__ = "borrowing_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"))
    status = Column(String)  # 'BORROWED' or 'RETURNED'

    user = relationship("User", back_populates="borrowing_records")
    book = relationship("Book", back_populates="borrowing_records")

User.borrowing_records = relationship("BorrowingRecord", back_populates="user", cascade="all, delete-orphan")
Book.borrowing_records = relationship("BorrowingRecord", back_populates="book", cascade="all, delete-orphan")