from fastapi import APIRouter, HTTPException, Request, Depends, Path, Query
from starlette import status
from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated, Generic, TypeVar, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import event, select, or_, func
from ..database import sessionlocal
from ..models import Posts, Comments, Likes
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


T = TypeVar('T')

class PostCreate(BaseModel):
    title:str = Field(alias='Title')
    content:str = Field(alias='Content')
    model_config = ConfigDict(populate_by_name=True)

class authorread(BaseModel):
    id:int 
    username:str

class Commentread(BaseModel, Generic[T]):
    id:int
    content:str
    user: T

    model_config = ConfigDict(from_attributes=True)

class PostRead(BaseModel):
    id:int
    title:str
    content:str
    slug:str
    author:authorread
    comments:list[Commentread[authorread] ]| None = None

    model_config = ConfigDict(from_attributes=True)

class PostUpdate(BaseModel):
    title:str
    content:str

class CommentCreate(BaseModel):
    content:str = Field(alias='Content')
    model_config = ConfigDict(populate_by_name=True)

@dataclass
class Pagination:
    limit:int=10
    offset:int=0

db_dependency = Annotated[Session, Depends(get_db)]
user_dependency = Annotated[dict, Depends(get_current_user)]

@router.get('/', status_code=status.HTTP_200_OK)
@limiter.limit('30/minute')
async def get_all_post(db:db_dependency, user:user_dependency, request:Request, paginate:Pagination=Depends(), search:Optional[str]=Query(None, min_length=3)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    
    if search:
        post_model = db.scalars(select(Posts).where(or_(Posts.title.ilike(f"%{search}%"), Posts.content.ilike(f"%{search}%"))).limit(paginate.limit).offset(paginate.offset)).all()
        total = db.scalar(select(func.count(Posts.id)).select_from(Posts).where(or_(Posts.title.ilike(f"%{search}%"), Posts.content.ilike(f"%{search}%"))))
        if not post_model:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No posts found matching the search criteria')
        return {'total':total, 'limit':paginate.limit, 'offset':paginate.offset, 'item':post_model}
    
    post_model = db.query(Posts).all()
    total = db.query(Posts).count()

    return {'total':total, 'limit':paginate.limit, 'offset':paginate.offset, 'item':post_model}

@router.post('/', status_code=status.HTTP_201_CREATED)
@limiter.limit('30/minute')
async def create_post(db:db_dependency, user:user_dependency, request:Request, newPost:PostCreate):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    
    post_model = Posts(**newPost.model_dump(), author_id=user.get('id'))
    db.add(post_model)
    db.commit()

@router.get('/{slug}', status_code=status.HTTP_200_OK, response_model=PostRead)
@limiter.limit('30/minute')
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

@router.get('/{post_id}/comments', status_code=status.HTTP_200_OK, response_model=list[Commentread[authorread]])
@limiter.limit('30/minute')
async def get_comment(db:db_dependency, user:user_dependency, request:Request, post_id:int=Path(gt=0)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    comments = db.query(Comments).filter(Comments.post_id == post_id).all()
    return comments

@router.post('/{post_id}/like')
async def like_post(db:db_dependency, user:user_dependency, post_id:int=Path(gt=0)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    
    post = db.scalar(select(Posts).where(Posts.id == post_id))
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Post not found')
    
    existing_like = db.scalar(select(Likes).where(Likes.post_id == post_id, Likes.user_id == user.get('id')))
    if existing_like:
        db.delete(existing_like)
        db.commit()
        return {'msg':'unliked'}
    
    new_like = Likes(user_id=user.get('id'), post_id=post_id)
    db.add(new_like)
    db.commit()
    return {'msg':'liked'}

@router.get('/{post_id}/likes-count', status_code=status.HTTP_200_OK)
@limiter.limit('30/minute')
async def like_count(db:db_dependency, user:user_dependency, request:Request, post_id:int=Path(gt=0)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Unauthorized')
    
    total_likes = db.scalar(select(func.count(Likes.id)).select_from(Likes).where(Likes.post_id == post_id))
    results = db.scalars(select(Likes).where(Likes.post_id == post_id))
    likers_list = results.all()
    likers = [liker.user.username for liker in likers_list]
    return {'total_likes':total_likes, 'likers':likers}

