from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
import config

def get_main_menu_keyboard(is_admin=False):
    if is_admin:
        buttons = [
            ["📚 Browse Subjects"],
            ["⚙️ Admin Panel"],
            ["ℹ️ Help"]
        ]
    else:
        buttons = [
            ["📚 Browse Subjects"],
            ["ℹ️ Help"]
        ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_subjects_keyboard():
    keyboard = []
    for code, name in config.SUBJECTS.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"subject_{code}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_main")])
    return InlineKeyboardMarkup(keyboard)

def get_chapters_keyboard(subject_id, action="browse"):
    from database import Session, Chapter
    session = Session()
    chapters = session.query(Chapter).filter_by(subject_id=subject_id).all()
    session.close()
    
    keyboard = []
    for chapter in chapters:
        keyboard.append([InlineKeyboardButton(chapter.name, callback_data=f"chapter_{action}_{chapter.id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_subjects")])
    return InlineKeyboardMarkup(keyboard)

def get_content_types_keyboard(chapter_id, action="browse"):
    keyboard = []
    for code, name in config.CONTENT_TYPES.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"content_{action}_{chapter_id}_{code}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data=f"back_to_chapters_{chapter_id}")])
    return InlineKeyboardMarkup(keyboard)

def get_admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("📖 Add/Delete Chapter", callback_data="admin_chapters")],
        [InlineKeyboardButton("➕ Add Content", callback_data="admin_add_content")],
        [InlineKeyboardButton("👥 Manage Users", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 Back to Main", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_user_management_keyboard(users):
    keyboard = []
    for user in users:
        status = "🚫 Blocked" if user.is_blocked else "✅ Active"
        btn_text = f"{user.first_name} - {status}"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"user_detail_{user.user_id}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin")])
    return InlineKeyboardMarkup(keyboard)

def get_user_action_keyboard(user_id, is_blocked):
    keyboard = []
    if is_blocked:
        keyboard.append([InlineKeyboardButton("✅ Unblock User", callback_data=f"unblock_user_{user_id}")])
    else:
        keyboard.append([InlineKeyboardButton("🚫 Block User", callback_data=f"block_user_{user_id}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_users")])
    return InlineKeyboardMarkup(keyboard)

def get_back_keyboard(target):
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data=target)]]
    return InlineKeyboardMarkup(keyboard)
