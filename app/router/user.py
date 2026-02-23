from fastapi import APIRouter, HTTPException, Request, Depends, Path
from starlette import status
from pydantic import BaseModel, Field, EmailStr
from passlib.context import CryptContext
from typing import Annotated
from sqlalchemy.orm import Session
from sqlalchemy import select
from ..database import sessionlocal
from ..models import Users, Posts
from ..limiter import limiter
from .auth import get_current_user
from datetime import datetime

router = APIRouter(
    prefix='/users',
    tags=['users']
)

def get_db():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

class UserCreate(BaseModel):
    username:str = Field(alias='userName')
    email:EmailStr = Field(alias='Email')
    password:str = Field(alias='Password')

class UserRead(BaseModel):
    id:int
    username:str
    email:EmailStr
    created_at:datetime

@router.post('/', status_code=status.HTTP_201_CREATED)
@limiter.limit('10/minute')
async def create_user(db:db_dependency, request:Request, newUser:UserCreate):
    user_model = Users(
        username=newUser.username,
        email=newUser.email,
        hashed_password=bcrypt_context.hash(newUser.password)
    )

    db.add(user_model)
    db.commit()

@router.get('/get', status_code=status.HTTP_200_OK, response_model=UserRead)
@limiter.limit('30/minute')
async def get_user(db:db_dependency, user:user_dependency, request:Request):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid token')
    
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    if not user_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='user not found')
    
    return user_model

@router.get('/posts', status_code=status.HTTP_200_OK)
@limiter.limit('30/minute')
async def get_user_post(db:db_dependency, user:user_dependency, request:Request):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid token')
    
    user_model = db.scalars(select(Users).where(Users.id == user.get('id'))).first()
    if not user_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='user not found')
    users_post = db.scalars(select(Posts).where(Posts.author_id == user_model.id)).all()
    return users_post


