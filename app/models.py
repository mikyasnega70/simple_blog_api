from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy_utils import EmailType
from sqlalchemy.sql import func
from .database import Base

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(EmailType, unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
 
class Posts(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(String)
    slug = Column(String, unique=True)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    author_id = Column(Integer, ForeignKey('users.id'))

class Comments(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    content = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey('users.id'))
    post_id = Column(Integer, ForeignKey('posts.id'))
