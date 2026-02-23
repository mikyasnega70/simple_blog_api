from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from .limiter import limiter
from .database import engine
from .models import Base
from .router import blog, auth, user

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.get('/')
async def test():
    return {'status':'healthy'}

app.include_router(blog.router)
app.include_router(auth.router)
app.include_router(user.router)
