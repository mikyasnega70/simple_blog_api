from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models import Base, Users, Posts, Comments
from app.router.auth import bcrypt_context
import pytest

DATABASE_URL = 'sqlite:///./test.db'
engine = create_engine(DATABASE_URL, connect_args={'check_same_thread':False}, poolclass=StaticPool)

Testsessionlocal = sessionmaker(autoflush=False, autocommit=False, bind=engine)

client = TestClient(app)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = Testsessionlocal()
    try:
        yield db
    finally:
        db.close()

def override_get_current_user():
    return {'id': 1, 'username': 'testuser'}

@pytest.fixture
def test_user():
    user = Users(
        username='testuser',
        email='test@gmail.com',
        hashed_password=bcrypt_context.hash('testpassword')
    )
    db = Testsessionlocal()
    db.add(user)
    db.commit()
    yield user
    with engine.connect() as conn:
        conn.execute(text('delete from users;'))
        conn.commit()

@pytest.fixture
def test_post():
    post = Posts(
        title='Test Post',
        content='This is a test post.',
        slug='test-post-1',
        author_id=1
    )
    db = Testsessionlocal()
    db.add(post)
    db.commit()
    yield post
    with engine.connect() as conn:
        conn.execute(text('delete from posts;'))
        conn.commit()



