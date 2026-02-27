from utils import *
from fastapi import status
from app.router.blog import get_db, get_current_user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

def test_create_post(test_post):
    response = client.post('/posts/', json={
        'title':'Test Post',
        'content':'This is a test post.'
    })
    assert response.status_code == status.HTTP_201_CREATED

def test_get_posts(test_post):
    response = client.get('/posts/')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        'total':1,
        'limit':10,
        'offset':0,
        'item': [{
            'id': 1,
            'title': 'Test Post',
            'content': 'This is a test post.',
            'slug': 'test-post-1',
            'is_published': False,
            'created_at': test_post.created_at.isoformat(),
            'updated_at': test_post.updated_at.isoformat() if test_post.updated_at else None,
            'author_id': 1
        }]
    }


        
    




