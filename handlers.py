from telegram import Update, ParseMode
from telegram.ext import CallbackContext, ConversationHandler
from telegram.error import BadRequest
import os
from datetime import datetime

import config
from database import Session, Subject, Chapter, Content
from keyboards import *
from utils import *

# Conversation states
SELECT_SUBJECT, ENTER_CHAPTER, CONFIRM_CHAPTER = range(3)
SELECT_SUBJECT_CONTENT, SELECT_CHAPTER_CONTENT, SELECT_CONTENT_TYPE, ENTER_CONTENT_NUMBER, SEND_CONTENT_FILE = range(5)

def start_command(update: Update, context: CallbackContext):
    user = update.effective_user
    db_user = get_user(user.id, user.username, user.first_name, user.last_name)
    
    if db_user.is_blocked:
        update.message.reply_text("🚫 You are currently blocked. Please try again later.")
        return
    
    welcome_message = """
    👋 *Hello! My name is Board Booster* 
    📚 *Here for your Board Exam Preparation*
    
    👨‍💻 *Created by Team Hackers*
    
    I provide comprehensive study materials including:
    • 🎥 Video Lectures
    • 📝 Detailed Notes  
    • 📊 Daily Practice Problems
    
    Get started by selecting a subject below! 👇
    """
    
    update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_main_menu_keyboard(is_admin=user.id in config.ADMIN_IDS)
    )
    log_user_action(user.id, "start")

def admin_command(update: Update, context: CallbackContext):
    user = update.effective_user
    
    if user.id not in config.ADMIN_IDS:
        update.message.reply_text("⛔ You are not authorized to access admin panel.")
        return
    
    update.message.reply_text(
        "⚙️ *Admin Panel*\nSelect an option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_admin_keyboard()
    )

def handle_message(update: Update, context: CallbackContext):
    user = update.effective_user
    db_user = get_user(user.id, user.username, user.first_name, user.last_name)
    
    if db_user.is_blocked:
        update.message.reply_text("🚫 You are currently blocked. Please try again later.")
        return
    
    text = update.message.text
    
    if text == "📚 Browse Subjects":
        update.message.reply_text(
            "📚 *Select a Subject:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_subjects_keyboard()
        )
    elif text == "⚙️ Admin Panel":
        admin_command(update, context)
    elif text == "ℹ️ Help":
        help_command(update, context)
    else:
        # Unauthorized message
        warnings = add_warning(user.id)
        remaining = config.MAX_WARNINGS - warnings
        
        if remaining > 0:
            update.message.reply_text(
                f"⚠️ *Warning {warnings}/{config.MAX_WARNINGS}*\n"
                f"Please use the menu buttons only. {remaining} warnings remaining before block.",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            update.message.reply_text(
                "🚫 You have been blocked for 24 hours due to multiple warnings. "
                "You will be automatically unblocked after 24 hours."
            )

def help_command(update: Update, context: CallbackContext):
    help_text = """
    *📖 Board Booster Help Guide*
    
    *How to use:*
    1. Tap '📚 Browse Subjects' to begin
    2. Select your subject from the list
    3. Choose a chapter
    4. Select content type (Lecture/Note/DPP)
    5. Enter content number
    
    *Content Types:*
    • 🎥 *Lecture*: Video explanations
    • 📝 *Note*: Detailed PDF notes
    • 📊 *DPP*: Daily Practice Problems
    
    *⚠️ Important:*
    • Use menu buttons only
    • Don't send random messages
    • 5 warnings = 24-hour block
    
    *Admin Commands:*
    • `/admin` - Access admin panel
    
    Need more help? Contact support.
    """
    
    update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

def callback_query_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user = query.from_user
    
    data = query.data
    
    # Browse Subjects Flow
    if data.startswith("subject_"):
        subject_code = data.split("_")[1]
        session = Session()
        subject = session.query(Subject).filter_by(code=subject_code).first()
        
        if subject:
            context.user_data['current_subject'] = subject.id
            query.edit_message_text(
                f"📖 *{subject.name}*\nSelect a chapter:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_chapters_keyboard(subject.id, "browse")
            )
        session.close()
    
    elif data.startswith("chapter_browse_"):
        chapter_id = int(data.split("_")[2])
        session = Session()
        chapter = session.query(Chapter).get(chapter_id)
        
        if chapter:
            context.user_data['current_chapter'] = chapter_id
            query.edit_message_text(
                f"📚 *{chapter.name}*\nSelect content type:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_content_types_keyboard(chapter_id, "browse")
            )
        session.close()
    
    elif data.startswith("content_browse_"):
        _, _, chapter_id, content_type = data.split("_")
        chapter_id = int(chapter_id)
        
        query.edit_message_text(
            f"Enter content number for {config.CONTENT_TYPES[content_type]}:"
        )
        context.user_data['browse_chapter'] = chapter_id
        context.user_data['browse_content_type'] = content_type
    
    # Admin Flow - Chapter Management
    elif data == "admin_chapters":
        query.edit_message_text(
            "📖 *Chapter Management*\nSelect a subject:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_subjects_keyboard()
        )
        context.user_data['admin_mode'] = 'chapters'
    
    elif data.startswith("subject_") and context.user_data.get('admin_mode') == 'chapters':
        subject_code = data.split("_")[1]
        session = Session()
        subject = session.query(Subject).filter_by(code=subject_code).first()
        
        if subject:
            context.user_data['admin_subject'] = subject.id
            keyboard = get_chapters_keyboard(subject.id, "admin")
            # Add "Add New Chapter" button
            keyboard.inline_keyboard.insert(0, [
                InlineKeyboardButton("➕ Add New Chapter", callback_data="add_chapter")
            ])
            
            query.edit_message_text(
                f"📖 *{subject.name} - Chapters*\nManage chapters:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        session.close()
    
    elif data == "add_chapter":
        query.edit_message_text(
            "Enter the name of the new chapter:"
        )
        return ENTER_CHAPTER
    
    elif data.startswith("chapter_admin_"):
        chapter_id = int(data.split("_")[2])
        session = Session()
        chapter = session.query(Chapter).get(chapter_id)
        
        if chapter:
            keyboard = [
                [InlineKeyboardButton("🗑️ Delete Chapter", callback_data=f"delete_chapter_{chapter_id}")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"subject_{chapter.subject.code}")]
            ]
            query.edit_message_text(
                f"Chapter: *{chapter.name}*\n\nSelect action:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        session.close()
    
    # Admin Flow - Add Content
    elif data == "admin_add_content":
        query.edit_message_text(
            "➕ *Add Content*\nSelect subject:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_subjects_keyboard()
        )
        context.user_data['admin_mode'] = 'add_content'
        return SELECT_SUBJECT_CONTENT
    
    # User Management
    elif data == "admin_users":
        session = Session()
        users = session.query(User).order_by(User.created_at.desc()).limit(50).all()
        session.close()
        
        query.edit_message_text(
            "👥 *User Management*\nSelect a user:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_user_management_keyboard(users)
        )
    
    elif data.startswith("user_detail_"):
        user_id = int(data.split("_")[2])
        session = Session()
        user = session.query(User).filter_by(user_id=user_id).first()
        session.close()
        
        if user:
            status = "🚫 Blocked" if user.is_blocked else "✅ Active"
            user_info = f"""
👤 *User Details:*
• Name: {user.first_name} {user.last_name or ''}
• Username: @{user.username or 'N/A'}
• User ID: `{user.user_id}`
• Status: {status}
• Warnings: {user.warnings}/{config.MAX_WARNINGS}
• Joined: {user.created_at.strftime('%Y-%m-%d %H:%M')}
"""
            query.edit_message_text(
                user_info,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_user_action_keyboard(user.user_id, user.is_blocked)
            )
    
    elif data.startswith("block_user_"):
        user_id = int(data.split("_")[2])
        block_user(user_id)
        query.answer("✅ User blocked successfully!")
        query.edit_message_reply_markup(
            get_user_action_keyboard(user_id, True)
        )
    
    elif data.startswith("unblock_user_"):
        user_id = int(data.split("_")[2])
        unblock_user(user_id)
        query.answer("✅ User unblocked successfully!")
        query.edit_message_reply_markup(
            get_user_action_keyboard(user_id, False)
        )
    
    # Navigation
    elif data == "back_to_main":
        query.edit_message_text(
            "🔙 Back to main menu",
            reply_markup=get_main_menu_keyboard(is_admin=user.id in config.ADMIN_IDS)
        )
    
    elif data == "back_to_subjects":
        query.edit_message_text(
            "📚 Select a Subject:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_subjects_keyboard()
        )
    
    elif data.startswith("back_to_chapters_"):
        chapter_id = int(data.split("_")[3])
        session = Session()
        chapter = session.query(Chapter).get(chapter_id)
        if chapter:
            query.edit_message_text(
                f"📚 *{chapter.name}*\nSelect content type:",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=get_content_types_keyboard(chapter_id, "browse")
            )
        session.close()
    
    elif data == "back_to_admin":
        query.edit_message_text(
            "⚙️ *Admin Panel*\nSelect an option:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_admin_keyboard()
        )

# Content sending handler
def send_content_number(update: Update, context: CallbackContext):
    user = update.effective_user
    db_user = get_user(user.id, user.username, user.first_name, user.last_name)
    
    if db_user.is_blocked:
        update.message.reply_text("🚫 You are currently blocked. Please try again later.")
        return
    
    try:
        content_number = int(update.message.text)
        chapter_id = context.user_data.get('browse_chapter')
        content_type = context.user_data.get('browse_content_type')
        
        if not chapter_id or not content_type:
            update.message.reply_text("❌ Error: Please start over from the beginning.")
            return
        
        session = Session()
        content = session.query(Content).filter_by(
            chapter_id=chapter_id,
            content_type=content_type,
            content_number=content_number
        ).first()
        
        if content:
            # Get file extension
            ext = "mp4" if content_type == "lecture" else "pdf"
            
            # Try to send using file_id if available
            if content.file_id:
                try:
                    if content_type == "lecture":
                        context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=content.file_id,
                            caption=f"🎥 Lecture #{content_number}"
                        )
                    else:
                        context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=content.file_id,
                            caption=f"📄 {config.CONTENT_TYPES[content_type]} #{content_number}"
                        )
                    log_user_action(user.id, f"downloaded_{content_type}_{content_number}")
                    return
                except BadRequest:
                    pass  # Fall back to file path
            
            # Send using file path
            if os.path.exists(content.file_path):
                with open(content.file_path, 'rb') as file:
                    if content_type == "lecture":
                        msg = context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=file,
                            caption=f"🎥 Lecture #{content_number}"
                        )
                        # Save file_id for future use
                        content.file_id = msg.video.file_id
                    else:
                        msg = context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=file,
                            caption=f"📄 {config.CONTENT_TYPES[content_type]} #{content_number}"
                        )
                        content.file_id = msg.document.file_id
                
                session.commit()
                log_user_action(user.id, f"downloaded_{content_type}_{content_number}")
            else:
                update.message.reply_text("❌ File not found. Please contact admin.")
        else:
            update.message.reply_text(f"❌ Content #{content_number} not found for selected type.")
        
        session.close()
        
        # Show subject selection again
        update.message.reply_text(
            "📚 Select a Subject:",
            reply_markup=get_subjects_keyboard()
        )
        
    except ValueError:
        update.message.reply_text("❌ Please enter a valid number.")
        add_warning(user.id)

# Admin conversation handlers
def add_chapter_name(update: Update, context: CallbackContext):
    chapter_name = update.message.text
    subject_id = context.user_data.get('admin_subject')
    
    if not subject_id:
        update.message.reply_text("❌ Error: Please start over.")
        return ConversationHandler.END
    
    session = Session()
    
    # Check if chapter already exists
    existing = session.query(Chapter).filter_by(
        subject_id=subject_id,
        name=chapter_name
    ).first()
    
    if existing:
        update.message.reply_text("❌ Chapter already exists!")
        session.close()
        return ConversationHandler.END
    
    # Add new chapter
    new_chapter = Chapter(
        subject_id=subject_id,
        name=chapter_name
    )
    session.add(new_chapter)
    session.commit()
    session.close()
    
    update.message.reply_text(f"✅ Chapter '{chapter_name}' added successfully!")
    
    # Return to admin panel
    update.message.reply_text(
        "⚙️ *Admin Panel*\nSelect an option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_admin_keyboard()
    )
    
    return ConversationHandler.END

def select_subject_content(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    subject_code = query.data.split("_")[1]
    session = Session()
    subject = session.query(Subject).filter_by(code=subject_code).first()
    
    if subject:
        context.user_data['content_subject'] = subject.id
        query.edit_message_text(
            f"➕ *Add Content to {subject.name}*\nSelect chapter:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_chapters_keyboard(subject.id, "add_content")
        )
    
    session.close()
    return SELECT_CHAPTER_CONTENT

def select_chapter_content(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    chapter_id = int(query.data.split("_")[2])
    context.user_data['content_chapter'] = chapter_id
    
    session = Session()
    chapter = session.query(Chapter).get(chapter_id)
    
    if chapter:
        query.edit_message_text(
            f"📚 *{chapter.name}*\nSelect content type:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=get_content_types_keyboard(chapter_id, "add")
        )
    
    session.close()
    return SELECT_CONTENT_TYPE

def select_content_type_admin(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    chapter_id = int(query.data.split("_")[2])
    content_type = query.data.split("_")[3]
    
    context.user_data['content_chapter'] = chapter_id
    context.user_data['content_type'] = content_type
    
    query.edit_message_text(
        f"Enter content number for {config.CONTENT_TYPES[content_type]}:"
    )
    
    return ENTER_CONTENT_NUMBER

def enter_content_number_admin(update: Update, context: CallbackContext):
    try:
        content_number = int(update.message.text)
        context.user_data['content_number'] = content_number
        
        # Check if content already exists
        session = Session()
        existing = session.query(Content).filter_by(
            chapter_id=context.user_data['content_chapter'],
            content_type=context.user_data['content_type'],
            content_number=content_number
        ).first()
        
        if existing:
            update.message.reply_text("❌ Content with this number already exists!")
            session.close()
            return ConversationHandler.END
        
        session.close()
        
        # Ask for file
        content_type = context.user_data['content_type']
        file_type = "MP4 video" if content_type == "lecture" else "PDF"
        
        update.message.reply_text(
            f"Please send the {file_type} file for {config.CONTENT_TYPES[content_type]} #{content_number}"
        )
        
        return SEND_CONTENT_FILE
        
    except ValueError:
        update.message.reply_text("❌ Please enter a valid number.")
        return ENTER_CONTENT_NUMBER

def save_content_file(update: Update, context: CallbackContext):
    # Get file
    if update.message.video:
        file = update.message.video
        expected_type = "lecture"
    elif update.message.document:
        file = update.message.document
        # Check if it's PDF
        if file.mime_type != "application/pdf":
            update.message.reply_text("❌ Please send a PDF file for notes/DPP.")
            return SEND_CONTENT_FILE
        expected_type = "note" if context.user_data['content_type'] == "note" else "dpp"
    else:
        update.message.reply_text("❌ Please send a valid file.")
        return SEND_CONTENT_FILE
    
    # Verify file type matches content type
    if context.user_data['content_type'] != expected_type:
        update.message.reply_text(
            f"❌ File type mismatch. Expected {context.user_data['content_type']}, got {expected_type}."
        )
        return SEND_CONTENT_FILE
    
    # Save file
    file_path = save_file(
        file.get_file(),
        context.user_data['content_type'],
        context.user_data['content_chapter'],
        context.user_data['content_number']
    )
    
    if not file_path:
        update.message.reply_text("❌ Error saving file.")
        return ConversationHandler.END
    
    # Save to database
    session = Session()
    new_content = Content(
        chapter_id=context.user_data['content_chapter'],
        content_type=context.user_data['content_type'],
        content_number=context.user_data['content_number'],
        file_path=file_path
    )
    session.add(new_content)
    session.commit()
    session.close()
    
    update.message.reply_text(
        f"✅ {config.CONTENT_TYPES[context.user_data['content_type']]} #{context.user_data['content_number']} added successfully!"
    )
    
    # Return to admin panel
    update.message.reply_text(
        "⚙️ *Admin Panel*\nSelect an option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=get_admin_keyboard()
    )
    
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Operation cancelled.",
        reply_markup=get_main_menu_keyboard(is_admin=update.effective_user.id in config.ADMIN_IDS)
    )
    return ConversationHandler.END
