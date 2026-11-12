import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from redis import Redis
from src.config.database import engine
from src.config.settings import SEED_DEMO,REDIS_URL
from src.config.migrate import ensure_schema
from src.models import *
from src.middlewares.request_id import RequestIDMiddleware
from src.middlewares.errors import ErrorMiddleware
from src.routes import auth,datasets,runs,policies,reviews,audit,archives
@asynccontextmanager
async def lifespan(app):
 ensure_schema()
 if SEED_DEMO:
  try:
   from scripts.seed_demo import seed
   seed()
  except Exception:logging.exception('Seed failure; startup continues')
 yield
app=FastAPI(title='澄湾管网漏损判别席',lifespan=lifespan)
app.add_middleware(ErrorMiddleware);app.add_middleware(RequestIDMiddleware)
for route in (auth,datasets,runs,policies,reviews,audit,archives):app.include_router(route.router)
@app.get('/health')
def health():
 with engine.connect() as c:c.execute(text('select 1'))
 Redis.from_url(REDIS_URL).ping();return {'status':'ok'}
