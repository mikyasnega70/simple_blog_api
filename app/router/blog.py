from fastapi import APIRouter, HTTPException, Depends
from starlette import status
from pydantic import BaseModel
from typing import Annotated
from sqlalchemy.orm import Session
from ..database import sessionlocal
from ..models import Posts, Comments

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

db_dependency = Annotated[Session, Depends(get_db)]

@router.get('/', status_code=status.HTTP_200_OK)
async def get_all_post(db:db_dependency):
    post_model = db.query(Posts).all()

    return post_model


