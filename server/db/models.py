from sqlalchemy import Column, UUID, JSON, DateTime, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Chat(Base):
    __tablename__ = 'chats'

    id = Column(UUID(as_uuid=True), primary_key=True, index=True)
    started_at = Column(DateTime, nullable=False, index=True)
    header = Column(String, nullable=True)

    messages = Column(JSON, nullable=False, default=list)

    def __str__(self):
        return f'{self.id}, {len(self.messages)} msgs'

    def __len__(self):
        return len(self.messages)
