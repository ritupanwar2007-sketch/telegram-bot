import os
from datetime import datetime, timedelta
from database import Session, User, UserAction
import config

def get_user(user_id, username=None, first_name=None, last_name=None):
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    
    if not user:
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name
        )
        session.add(user)
        session.commit()
    else:
        user.last_active = datetime.utcnow()
        user.username = username or user.username
        user.first_name = first_name or user.first_name
        user.last_name = last_name or user.last_name
        session.commit()
    
    # Check if block duration has expired
    if user.is_blocked and user.blocked_until and datetime.utcnow() > user.blocked_until:
        user.is_blocked = False
        user.warnings = 0
        user.blocked_until = None
        session.commit()
    
    session.close()
    return user

def log_user_action(user_id, action):
    session = Session()
    user_action = UserAction(user_id=user_id, action=action)
    session.add(user_action)
    session.commit()
    session.close()

def add_warning(user_id):
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.warnings += 1
        if user.warnings >= config.MAX_WARNINGS:
            user.is_blocked = True
            user.blocked_until = datetime.utcnow() + timedelta(seconds=config.BLOCK_DURATION)
        session.commit()
    session.close()
    return user.warnings if user else 0

def block_user(user_id):
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.is_blocked = True
        user.blocked_until = datetime.utcnow() + timedelta(seconds=config.BLOCK_DURATION)
        session.commit()
    session.close()

def unblock_user(user_id):
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.is_blocked = False
        user.warnings = 0
        user.blocked_until = None
        session.commit()
    session.close()

def save_file(file, content_type, chapter_id, content_number):
    # Determine directory based on content type
    if content_type == "lecture":
        directory = config.LECTURES_DIR
        ext = "mp4"
    elif content_type == "note":
        directory = config.NOTES_DIR
        ext = "pdf"
    elif content_type == "dpp":
        directory = config.DPP_DIR
        ext = "pdf"
    else:
        return None
    
    # Create filename
    filename = f"{chapter_id}_{content_number}_{content_type}.{ext}"
    file_path = os.path.join(directory, filename)
    
    # Save file
    file.download(file_path)
    
    return file_path
