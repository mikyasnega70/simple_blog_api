from utils import *
from fastapi import status
from app.router.auth import get_db

app.dependency_overrides[get_db] = override_get_db

def test_login(test_user):
    response = client.post('/auth/token', data={
        'username':'test@gmail.com',
        'password':'testpassword'
    })
    assert response.status_code == status.HTTP_200_OK
    assert 'access_token' in response.json()

def test_login_invalid_credentials(test_user):
    response = client.post('/auth/token', data={
        'username':'wrongname',
        'password':'wrongpassword'
    })
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.json()['detail'] == 'invalid credentials'








