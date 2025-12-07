import os
import shutil
from datetime import datetime, timedelta
from database import Session, User, UserAction, Chapter, Content
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
    
    # Check if block duration has expired (skip for admins)
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
    # Skip warning addition for admins
    if user_id in config.ADMIN_IDS:
        return 0
        
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.warnings += 1
        if user.warnings >= config.MAX_WARNINGS:
            user.is_blocked = True
            user.blocked_until = datetime.utcnow() + timedelta(seconds=config.BLOCK_DURATION)
        session.commit()
        warnings = user.warnings
    else:
        warnings = 0
    
    session.close()
    return warnings

def block_user(user_id):
    # Don't block admins
    if user_id in config.ADMIN_IDS:
        return False
    
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.is_blocked = True
        user.blocked_until = datetime.utcnow() + timedelta(seconds=config.BLOCK_DURATION)
        user.warnings = config.MAX_WARNINGS  # Set to max warnings
        session.commit()
        session.close()
        return True
    session.close()
    return False

def unblock_user(user_id):
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.is_blocked = False
        user.warnings = 0
        user.blocked_until = None
        session.commit()
        session.close()
        return True
    session.close()
    return False

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

def delete_chapter(chapter_id):
    """Delete a chapter and all its associated content and files"""
    session = Session()
    try:
        chapter = session.query(Chapter).get(chapter_id)
        if not chapter:
            return False
        
        # Get all contents for this chapter
        contents = session.query(Content).filter_by(chapter_id=chapter_id).all()
        
        # Delete associated files
        for content in contents:
            if os.path.exists(content.file_path):
                os.remove(content.file_path)
        
        # Delete chapter (contents will be deleted due to cascade)
        session.delete(chapter)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error deleting chapter: {e}")
        return False
    finally:
        session.close()

def delete_content(content_id):
    """Delete specific content and its file"""
    session = Session()
    try:
        content = session.query(Content).get(content_id)
        if not content:
            return False
        
        # Delete file
        if os.path.exists(content.file_path):
            os.remove(content.file_path)
        
        # Delete content from database
        session.delete(content)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Error deleting content: {e}")
        return False
    finally:
        session.close()

def get_user_stats(user_id):
    """Get statistics for a user"""
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    
    if not user:
        session.close()
        return None
    
    # Count user actions
    actions_count = session.query(UserAction).filter_by(user_id=user_id).count()
    
    # Get last 10 actions
    recent_actions = session.query(UserAction).filter_by(user_id=user_id)\
        .order_by(UserAction.timestamp.desc())\
        .limit(10)\
        .all()
    
    session.close()
    
    return {
        'user': user,
        'actions_count': actions_count,
        'recent_actions': recent_actions
    }

def get_bot_stats():
    """Get overall bot statistics"""
    session = Session()
    
    total_users = session.query(User).count()
    active_users = session.query(User).filter_by(is_blocked=False).count()
    blocked_users = session.query(User).filter_by(is_blocked=True).count()
    total_chapters = session.query(Chapter).count()
    total_contents = session.query(Content).count()
    
    # Get today's active users
    today = datetime.utcnow().date()
    today_users = session.query(User)\
        .filter(User.last_active >= datetime.combine(today, datetime.min.time()))\
        .count()
    
    session.close()
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'blocked_users': blocked_users,
        'today_active': today_users,
        'total_chapters': total_chapters,
        'total_contents': total_contents
    }

def cleanup_old_files():
    """Clean up orphaned files (files not referenced in database)"""
    session = Session()
    
    # Get all file paths from database
    db_files = set()
    contents = session.query(Content.file_path).all()
    for content in contents:
        if content.file_path:
            db_files.add(content.file_path)
    
    session.close()
    
    # Check all storage directories
    deleted_count = 0
    for directory in [config.LECTURES_DIR, config.NOTES_DIR, config.DPP_DIR]:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if file_path not in db_files:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        print(f"Deleted orphaned file: {file_path}")
                    except Exception as e:
                        print(f"Error deleting file {file_path}: {e}")
    
    return deleted_count

def export_user_data(user_id):
    """Export all data for a user (for GDPR compliance)"""
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    
    if not user:
        session.close()
        return None
    
    # Get all user actions
    actions = session.query(UserAction).filter_by(user_id=user_id)\
        .order_by(UserAction.timestamp)\
        .all()
    
    session.close()
    
    # Format data
    user_data = {
        'user_info': {
            'user_id': user.user_id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_blocked': user.is_blocked,
            'warnings': user.warnings,
            'blocked_until': user.blocked_until.isoformat() if user.blocked_until else None,
            'created_at': user.created_at.isoformat(),
            'last_active': user.last_active.isoformat()
        },
        'actions': [
            {
                'action': action.action,
                'timestamp': action.timestamp.isoformat()
            }
            for action in actions
        ]
    }
    
    return user_data

def backup_database():
    """Create a backup of the database"""
    if config.DATABASE_URL.startswith('sqlite'):
        # SQLite backup
        db_path = config.DATABASE_URL.replace('sqlite:///', '')
        backup_path = f"{db_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            import sqlite3
            source = sqlite3.connect(db_path)
            backup = sqlite3.connect(backup_path)
            source.backup(backup)
            source.close()
            backup.close()
            return backup_path
        except Exception as e:
            print(f"Error backing up SQLite database: {e}")
            return None
    else:
        # PostgreSQL backup would need pg_dump
        print("PostgreSQL backup requires pg_dump utility")
        return None

def reset_user_warnings(user_id):
    """Reset warnings for a user"""
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        user.warnings = 0
        session.commit()
        session.close()
        return True
    session.close()
    return False

def is_admin(user_id):
    """Check if user is admin"""
    return user_id in config.ADMIN_IDS

def can_bypass_restrictions(user_id):
    """Check if user can bypass restrictions (admins only)"""
    return user_id in config.ADMIN_IDS

def get_admin_ids():
    """Get list of admin IDs"""
    return config.ADMIN_IDS

def add_admin(user_id):
    """Add a new admin (only works if called by existing admin)"""
    if user_id not in config.ADMIN_IDS:
        # Update config.ADMIN_IDS
        config.ADMIN_IDS.append(user_id)
        
        # In a production environment, you would save this to a persistent storage
        # For now, we'll just update the runtime config
        return True
    return False

def remove_admin(user_id):
    """Remove an admin (cannot remove yourself)"""
    if user_id in config.ADMIN_IDS and len(config.ADMIN_IDS) > 1:
        config.ADMIN_IDS.remove(user_id)
        return True
    return False
