from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy_utils import EmailType
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Users(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    email = Column(EmailType, unique=True)
    hashed_password = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    posts = relationship('Posts', back_populates='author', cascade='all, delete-orphan')
    comments = relationship('Comments', back_populates='user', cascade='all, delete-orphan') 
 
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

    author = relationship('Users', back_populates='posts')
    comments = relationship('Comments', back_populates='post', cascade='all, delete-orphan')

class Comments(Base):
    __tablename__ = 'comments'

    id = Column(Integer, primary_key=True)
    content = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey('users.id'))
    post_id = Column(Integer, ForeignKey('posts.id'))

    user = relationship('Users', back_populates='comments')
    post = relationship('Posts', back_populates='comments')
