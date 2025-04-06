import os.path
import shutil
from uuid import uuid4

from fastapi import Depends, APIRouter
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only

from db.models import Chat
from db.session import get_db

chat_router = APIRouter()


@chat_router.get('/chats')
async def get_chats(db: AsyncSession = Depends(get_db)):
    query = select(Chat).options(load_only(Chat.id, Chat.started_at, Chat.header)).order_by(desc('started_at'))

    result = await db.execute(query)
    result = result.scalars()

    return jsonable_encoder(list(result))


@chat_router.get('/chat/{chat_id}')
async def get_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    query = select(Chat).filter(Chat.id == chat_id)
    result = await db.execute(query)
    return jsonable_encoder(result.scalar())


@chat_router.post('/chat/new')
async def chat_new():
    return str(uuid4())


@chat_router.delete('/chat/{chat_id}')
async def delete_chat(chat_id: str, db: AsyncSession = Depends(get_db)):
    query = delete(Chat).filter(Chat.id == chat_id)
    await db.execute(query)
    await db.commit()

    if os.path.exists(f'/tts_output/{chat_id}'):
        shutil.rmtree(f'/tts_output/{chat_id}')

    return {'id': chat_id}
