import uuid

from sqlalchemy import Column, UUID, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Configuration(Base):
    __tablename__ = 'configs'

    id = Column(Integer, autoincrement=True, index=True, primary_key=True)

    config = Column(JSON)


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)

    messages = Column(JSON)
