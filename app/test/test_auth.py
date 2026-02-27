from utils import *
from fastapi import status, HTTPException
from app.router.auth import get_db, authenticate_user, create_access_token, SECRET_KEY, ALGORITHM, get_current_user
from jose import jwt, JWTError
from datetime import timedelta

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

def test_authenticate_user(test_user):
    db = Testsessionlocal()
    authenticated_user = authenticate_user(test_user.email, 'testpassword',db)
    assert authenticated_user is not None
    assert authenticated_user.email == test_user.email

    wrong_user = authenticate_user('wrong', 'password', db)
    assert wrong_user is False

def test_create_access_token(test_user):
    token = create_access_token(test_user.email, test_user.id, timedelta(minutes=30))
    assert token is not None

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    assert payload['sub'] == test_user.email
    assert payload['id'] == test_user.id

@pytest.mark.asyncio
async def test_get_current_user(test_user):
    token = create_access_token(test_user.email, test_user.id, timedelta(minutes=30))
    user = await get_current_user(token)
    assert user is not None
    assert user['email'] == test_user.email
    assert user['id'] == test_user.id

@pytest.mark.asyncio
async def test_get_current_user_invalid_token(test_user):
    encode = {'email':'test@gmail.com'}
    token = jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)
    with pytest.raises(HTTPException) as excinfo:
        await get_current_user(token)

        assert excinfo.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert excinfo.value.detail == 'invalid credentials'













