from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text

from app.database import Base


class KnowledgeDoc(Base):
    __tablename__ = "knowledge_docs"
    id = Column(Integer, primary_key=True)
    title = Column(String(256), nullable=False)
    source_path = Column(String(512), nullable=False)
    status = Column(String(32), default="pending")  # pending|ingested|failed
    created_at = Column(DateTime, default=datetime.utcnow)


class AvatarConfig(Base):
    __tablename__ = "avatar_configs"
    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    image_path = Column(String(512), nullable=False)
    voice = Column(String(128), default="zh-CN-XiaoxiaoNeural")
    is_active = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatLog(Base):
    __tablename__ = "chat_logs"
    id = Column(Integer, primary_key=True)
    session_id = Column(String(64), index=True)
    role = Column(String(16))  # user|assistant
    content = Column(Text)
    latency_sec = Column(Integer, default=0)
    sentiment = Column(String(16))  # pos|neu|neg
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    extra = Column(JSON)
