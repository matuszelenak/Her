import os

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_USER = os.environ.get('POSTGRES_USER')
DATABASE_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
DATABASE_HOST = os.environ.get('POSTGRES_HOST')
DATABASE_PORT = os.environ.get('POSTGRES_PORT')
DATABASE_NAME = os.environ.get('POSTGRES_DB')
DATABASE_URL = f"postgresql+asyncpg://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"


engine = create_async_engine(DATABASE_URL)
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_db() -> AsyncSession:
    db = SessionLocal()
    try:
        yield db
    finally:
        await db.close()
