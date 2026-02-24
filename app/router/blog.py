from fastapi import APIRouter, HTTPException, Request, Depends, Path
from starlette import status
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated
from sqlalchemy.orm import Session
from sqlalchemy import event
from ..database import sessionlocal
from ..models import Posts, Comments
from .auth import get_current_user
from ..limiter import limiter
import string, random, uuid, re

router = APIRouter(
    prefix='/posts',
    tags=['posts']
)

def get_db():
    db = sessionlocal()
    try:
        yield db
    finally:
        db.close()

def generate_slug(db:Session, title:str, max_limit=10):
    for _ in range(max_limit):
        slug = re.sub(r'[^a-zA-Z0-9]+', '-', title.lower()).strip('-')
        slug = f"{slug}-{uuid.uuid4().hex[:6]}"
        exists = db.query(Posts).filter(Posts.slug == slug).first()
        if not exists:
            return slug

@event.listens_for(Posts, "before_insert")
def set_slug(mapper, connection, target):
    if not target.slug:
        session = Session(bind=connection)
        target.slug = generate_slug(db=session, title=target.title)

class PostCreate(BaseModel):
    title:str = Field(alias='Title')
    content:str = Field(alias='Content')
    model_config = ConfigDict(populate_by_name=True)

class PostUpdate(BaseModel):
    title:str
    content:str

class CommentCreate(BaseModel):
    content:str = Field(alias='Content')
    model_config = ConfigDict(populate_by_name=True)

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.get('/', status_code=status.HTTP_200_OK)
async def get_all_post(db:db_dependency):
    post_model = db.query(Posts).all()

    return post_model

@router.post('/', status_code=status.HTTP_201_CREATED)
@limiter.limit('30/minute')
async def create_post(db:db_dependency, user:user_dependency, request:Request, newPost:PostCreate):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    
    post_model = Posts(**newPost.model_dump(), author_id=user.get('id'))
    db.add(post_model)
    db.commit()

@router.get('/{slug}', status_code=status.HTTP_200_OK)
async def get_post(db:db_dependency, user:user_dependency, request:Request, slug:str):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    post  = db.query(Posts).filter(Posts.slug == slug).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found')
    
    return post

@router.put('/{id}', status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit('30/minute')
async def update_post(db:db_dependency, user:user_dependency, request:Request, update:PostUpdate, id:int=Path(gt=0)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    
    post_model = db.query(Posts).filter(Posts.id == id, Posts.author_id == user.get('id')).first()
    if not post_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found')
    
    post_model.title = update.title
    post_model.content = update.content

    db.add(post_model)
    db.commit()

@router.patch('/{id}', status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit('30/minute')
async def publish_post(db:db_dependency, user:user_dependency, request:Request, update:PostUpdate, id:int=Path(gt=0)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    
    post_model = db.query(Posts).filter(Posts.id == id, Posts.author_id == user.get('id')).first()
    if not post_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found')
    
    post_model.is_published = True
    

    db.add(post_model)
    db.commit()

@router.delete('/{id}', status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit('30/minute')
async def delete_post(db:db_dependency, user:user_dependency, request:Request, id:int=Path(gt=0)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    
    post_model = db.query(Posts).filter(Posts.id == id, Posts.author_id == user.get('id')).first()
    if not post_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found')
    
    db.delete(post_model)
    db.commit()

@router.post('/{post_id}/comments', status_code=status.HTTP_201_CREATED)
@limiter.limit('30/minute')
async def add_comment(db:db_dependency, user:user_dependency, request:Request, newcomment:CommentCreate, post_id:int=Path(gt=0)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    comment = Comments(**newcomment.model_dump(), user_id=user.get('id'), post_id=post_id)
    db.add(comment)
    db.commit()

@router.get('/{post_id}/comments', status_code=status.HTTP_200_OK)
@limiter.limit('30/minute')
async def get_comment(db:db_dependency, user:user_dependency, request:Request, post_id:int=Path(gt=0)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    comments = db.query(Comments).filter(Comments.post_id == post_id).all()
    return comments

