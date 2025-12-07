from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import config

Base = declarative_base()
engine = create_engine(config.DATABASE_URL)
Session = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_blocked = Column(Boolean, default=False)
    warnings = Column(Integer, default=0)
    blocked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

class Subject(Base):
    __tablename__ = 'subjects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    code = Column(String(20), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Chapter(Base):
    __tablename__ = 'chapters'
    
    id = Column(Integer, primary_key=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    name = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    subject = relationship("Subject", backref="chapters")
    contents = relationship("Content", back_populates="chapter", cascade="all, delete-orphan")

class Content(Base):
    __tablename__ = 'contents'
    
    id = Column(Integer, primary_key=True)
    chapter_id = Column(Integer, ForeignKey('chapters.id'), nullable=False)
    content_type = Column(String(20), nullable=False)  # lecture, note, dpp
    content_number = Column(Integer, nullable=False)
    file_path = Column(String(500), nullable=False)
    file_id = Column(String(200))  # Telegram file_id for faster sending
    created_at = Column(DateTime, default=datetime.utcnow)
    
    chapter = relationship("Chapter", back_populates="contents", overlaps="contents")

class UserAction(Base):
    __tablename__ = 'user_actions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    action = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

def init_db():
    Base.metadata.create_all(engine)
    
    # Add default subjects if they don't exist
    session = Session()
    for code, name in config.SUBJECTS.items():
        if not session.query(Subject).filter_by(code=code).first():
            session.add(Subject(name=name, code=code))
    session.commit()
    session.close()
