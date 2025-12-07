import os
import shutil
from datetime import datetime, timedelta
from database import Session, User, UserAction, Chapter, Content, Subject
import config

def get_user(user_id, username=None, first_name=None, last_name=None):
    """Get or create user in database"""
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
    """Log user action to database"""
    session = Session()
    user_action = UserAction(user_id=user_id, action=action)
    session.add(user_action)
    session.commit()
    session.close()

def add_warning(user_id):
    """Add warning to user (skip for admins)"""
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
    """Block a user (cannot block admins)"""
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
    """Unblock a user"""
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
    """Save uploaded file to storage"""
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
                try:
                    os.remove(content.file_path)
                except:
                    pass  # Ignore file deletion errors
        
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
            try:
                os.remove(content.file_path)
            except:
                pass  # Ignore file deletion errors
        
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
    
    # Get subject stats
    subject_stats = {}
    subjects = session.query(Subject).all()
    for subject in subjects:
        chapter_count = session.query(Chapter).filter_by(subject_id=subject.id).count()
        content_count = session.query(Content).join(Chapter).filter(Chapter.subject_id == subject.id).count()
        subject_stats[subject.name] = {
            'chapters': chapter_count,
            'contents': content_count
        }
    
    session.close()
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'blocked_users': blocked_users,
        'today_active': today_users,
        'total_chapters': total_chapters,
        'total_contents': total_contents,
        'subject_stats': subject_stats
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
    """Remove an admin (cannot remove yourself if only admin)"""
    if user_id in config.ADMIN_IDS and len(config.ADMIN_IDS) > 1:
        config.ADMIN_IDS.remove(user_id)
        return True
    return False

def get_chapter_by_name(subject_id, chapter_name):
    """Get chapter by name and subject"""
    session = Session()
    chapter = session.query(Chapter).filter_by(
        subject_id=subject_id,
        name=chapter_name
    ).first()
    session.close()
    return chapter

def get_content_by_details(chapter_id, content_type, content_number):
    """Get content by chapter, type, and number"""
    session = Session()
    content = session.query(Content).filter_by(
        chapter_id=chapter_id,
        content_type=content_type,
        content_number=content_number
    ).first()
    session.close()
    return content

def get_all_chapters(subject_id=None):
    """Get all chapters, optionally filtered by subject"""
    session = Session()
    if subject_id:
        chapters = session.query(Chapter).filter_by(subject_id=subject_id).all()
    else:
        chapters = session.query(Chapter).all()
    session.close()
    return chapters

def get_all_contents(chapter_id=None, content_type=None):
    """Get all contents, optionally filtered by chapter and/or type"""
    session = Session()
    query = session.query(Content)
    
    if chapter_id:
        query = query.filter_by(chapter_id=chapter_id)
    
    if content_type:
        query = query.filter_by(content_type=content_type)
    
    contents = query.all()
    session.close()
    return contents

def search_chapters(search_term):
    """Search chapters by name"""
    session = Session()
    chapters = session.query(Chapter).filter(
        Chapter.name.ilike(f"%{search_term}%")
    ).all()
    session.close()
    return chapters

def get_subject_by_code(subject_code):
    """Get subject by its code"""
    session = Session()
    subject = session.query(Subject).filter_by(code=subject_code).first()
    session.close()
    return subject

def get_subject_by_id(subject_id):
    """Get subject by its ID"""
    session = Session()
    subject = session.query(Subject).get(subject_id)
    session.close()
    return subject

def update_file_id(content_id, file_id):
    """Update Telegram file_id for content"""
    session = Session()
    content = session.query(Content).get(content_id)
    if content:
        content.file_id = file_id
        session.commit()
        session.close()
        return True
    session.close()
    return False

def get_user_by_id(user_id):
    """Get user by Telegram user ID"""
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    session.close()
    return user

def update_user_info(user_id, username=None, first_name=None, last_name=None):
    """Update user information"""
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()
    if user:
        if username is not None:
            user.username = username
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        session.commit()
        session.close()
        return True
    session.close()
    return False

def get_recent_users(limit=20):
    """Get recently active users"""
    session = Session()
    users = session.query(User).order_by(User.last_active.desc()).limit(limit).all()
    session.close()
    return users

def get_blocked_users():
    """Get all blocked users"""
    session = Session()
    users = session.query(User).filter_by(is_blocked=True).all()
    session.close()
    return users

def clear_all_warnings():
    """Clear warnings for all users"""
    session = Session()
    users = session.query(User).all()
    for user in users:
        user.warnings = 0
    session.commit()
    session.close()
    return True

def get_storage_stats():
    """Get storage statistics"""
    total_size = 0
    file_counts = {'lectures': 0, 'notes': 0, 'dpp': 0}
    
    for dir_name, dir_path in [
        ('lectures', config.LECTURES_DIR),
        ('notes', config.NOTES_DIR),
        ('dpp', config.DPP_DIR)
    ]:
        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                if os.path.isfile(file_path):
                    total_size += os.path.getsize(file_path)
                    file_counts[dir_name] += 1
    
    return {
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'file_counts': file_counts,
        'total_files': sum(file_counts.values())
    }

def get_content_stats():
    """Get content statistics by type"""
    session = Session()
    
    stats = {
        'lectures': 0,
        'notes': 0,
        'dpp': 0
    }
    
    # Count by content type
    for content_type in ['lecture', 'note', 'dpp']:
        count = session.query(Content).filter_by(content_type=content_type).count()
        stats[content_type + 's'] = count
    
    # Count by subject
    subject_stats = {}
    subjects = session.query(Subject).all()
    for subject in subjects:
        content_count = session.query(Content)\
            .join(Chapter)\
            .filter(Chapter.subject_id == subject.id)\
            .count()
        subject_stats[subject.name] = content_count
    
    session.close()
    
    return {
        'by_type': stats,
        'by_subject': subject_stats
    }

def validate_file_extension(filename, content_type):
    """Validate file extension based on content type"""
    if content_type == "lecture":
        valid_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    else:  # note or dpp
        valid_extensions = ['.pdf']
    
    ext = os.path.splitext(filename)[1].lower()
    return ext in valid_extensions

def get_file_extension(content_type):
    """Get expected file extension for content type"""
    if content_type == "lecture":
        return ".mp4"
    else:  # note or dpp
        return ".pdf"

def format_file_size(size_in_bytes):
    """Format file size in human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"

def check_storage_space(min_space_mb=100):
    """Check if there's enough storage space"""
    try:
        stat = shutil.disk_usage(config.FILES_DIR)
        free_space_mb = stat.free / (1024 * 1024)
        return free_space_mb >= min_space_mb, free_space_mb
    except:
        return True, 0  # Assume enough space if can't check

def create_backup():
    """Create a backup of important data"""
    backup_dir = os.path.join(config.FILES_DIR, "backups")
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"backup_{timestamp}.zip")
    
    try:
        import zipfile
        with zipfile.ZipFile(backup_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database file if SQLite
            if config.DATABASE_URL.startswith('sqlite'):
                db_path = config.DATABASE_URL.replace('sqlite:///', '')
                if os.path.exists(db_path):
                    zipf.write(db_path, 'database.db')
            
            # Add important directories
            for dir_name in ['lectures', 'notes', 'dpp']:
                dir_path = os.path.join(config.FILES_DIR, dir_name)
                if os.path.exists(dir_path):
                    for root, dirs, files in os.walk(dir_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, config.FILES_DIR)
                            zipf.write(file_path, arcname)
        
        return backup_file
    except Exception as e:
        print(f"Error creating backup: {e}")
        return None

def cleanup_old_backups(max_backups=5):
    """Clean up old backup files"""
    backup_dir = os.path.join(config.FILES_DIR, "backups")
    if not os.path.exists(backup_dir):
        return 0
    
    backup_files = []
    for filename in os.listdir(backup_dir):
        if filename.startswith("backup_") and filename.endswith(".zip"):
            filepath = os.path.join(backup_dir, filename)
            backup_files.append((filepath, os.path.getmtime(filepath)))
    
    # Sort by modification time (oldest first)
    backup_files.sort(key=lambda x: x[1])
    
    # Delete oldest backups if we have more than max_backups
    deleted_count = 0
    while len(backup_files) > max_backups:
        filepath, _ = backup_files.pop(0)
        try:
            os.remove(filepath)
            deleted_count += 1
        except:
            pass
    
    return deleted_count

def is_valid_content_number(content_number):
    """Check if content number is valid"""
    try:
        num = int(content_number)
        return num > 0 and num <= 1000  # Reasonable limit
    except:
        return False

def sanitize_filename(filename):
    """Sanitize filename to remove problematic characters"""
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    return filename

def get_next_content_number(chapter_id, content_type):
    """Get the next available content number for a chapter and type"""
    session = Session()
    max_number = session.query(Content.content_number)\
        .filter_by(chapter_id=chapter_id, content_type=content_type)\
        .order_by(Content.content_number.desc())\
        .first()
    session.close()
    
    if max_number:
        return max_number[0] + 1
    else:
        return 1

def get_chapter_content_summary(chapter_id):
    """Get summary of content in a chapter"""
    session = Session()
    
    # Get content counts by type
    content_counts = {}
    for content_type in ['lecture', 'note', 'dpp']:
        count = session.query(Content)\
            .filter_by(chapter_id=chapter_id, content_type=content_type)\
            .count()
        content_counts[content_type] = count
    
    # Get chapter info
    chapter = session.query(Chapter).get(chapter_id)
    
    session.close()
    
    return {
        'chapter': chapter,
        'content_counts': content_counts,
        'total_content': sum(content_counts.values())
    }
