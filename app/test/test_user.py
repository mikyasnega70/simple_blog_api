from utils import *
from fastapi import status
from app.router.user import get_db, get_current_user

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user

def test_create_user(test_user):
    response = client.post('/users/', json={
        'userName':'newuser',
        'Email':'new@gmail.com',
        'Password':'newpassword'
    })
    assert response.status_code == status.HTTP_201_CREATED

def test_get_user(test_user):
    response = client.get('/users/get')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {
        'id': 1,
        'username': 'testuser',
        'email': 'test@gmail.com',
        'created_at': test_user.created_at.isoformat()
    }

def test_get_user_post(test_user, test_post):
    response = client.get('/users/posts')
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == [
        {
            'id': 1,
            'title': 'Test Post',
            'content': 'This is a test post.',
            'slug': 'test-post-1',
            'is_published': False,
            'created_at': test_post.created_at.isoformat(),
            'updated_at': test_post.updated_at.isoformat() if test_post.updated_at else None,
            'author_id': 1
        }
    ]






