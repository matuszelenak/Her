import uuid

from sqlalchemy import Column, UUID, JSON, Integer, DateTime, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Configuration(Base):
    __tablename__ = 'configs'

    id = Column(Integer, autoincrement=True, index=True, primary_key=True)

    config = Column(JSON)


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    started_at = Column(DateTime, nullable=False, index=True)
    header = Column(String, nullable=True)

    messages = Column(JSON)

    def __str__(self):
        return f'{self.id}, {len(self.messages)} msgs'
