from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from starlette import status
from pydantic import BaseModel, Field, EmailStr
from passlib.context import CryptContext
from typing import Annotated
from sqlalchemy.orm import Session
from ..database import sessionlocal
from ..models import Users
from ..limiter import limiter
from jose import jwt, JWTError
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import os

router = APIRouter(
    prefix='/auth',
    tags=['auth']
)

load_dotenv()
SECRET_KEY = os.getenv('SECRET_KEY')
ALGORITHM = 'HS256'
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

def get_db():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]
outh2_bearer = OAuth2PasswordBearer(tokenUrl='/auth/token')

class UserLogin(BaseModel):
    email:EmailStr = Field(alias='Email')
    password:str = Field(alias='Password')

class Token(BaseModel):
    access_token:str
    token_type:str

def authenticate_user(email:EmailStr, password:str, db:Session):
    user = db.query(Users).filter(Users.email == email).first()
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(email:EmailStr, id:int, expires:timedelta):
    encode = {'sub':email, 'id':id}
    expire = datetime.now(timezone.utc) + expires
    encode.update({'exp':expire})
    token = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

async def get_current_user(token:Annotated[str, Depends(outh2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email:EmailStr = payload.get('sub')
        id:int = payload.get('id')
        if email is None or id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid credentials')
        return {'email':email, 'id':id}
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid credentials')

@router.post('/token', response_model=Token)
@limiter.limit('30/minute')
async def login_access(db:db_dependency, request:Request, form:Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = authenticate_user(form.username, form.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='invalid credentials')
    
    token = create_access_token(user.email, user.id, timedelta(minutes=30))
    return {'access_token':token, 'token_type':'bearer'}



