from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
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

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user(user.id, user.username, user.first_name, user.last_name)
    
    if db_user.is_blocked and user.id not in config.ADMIN_IDS:
        await update.message.reply_text("🚫 You are currently blocked. Please try again later.")
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
    
    await update.message.reply_text(
        welcome_message,
        parse_mode='Markdown',
        reply_markup=get_main_menu_keyboard(is_admin=user.id in config.ADMIN_IDS)
    )
    log_user_action(user.id, "start")

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to access admin panel.")
        return
    
    await update.message.reply_text(
        "⚙️ *Admin Panel*\nSelect an option:",
        parse_mode='Markdown',
        reply_markup=get_admin_keyboard()
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check if user is admin
    if user.id in config.ADMIN_IDS:
        text = update.message.text
        
        if text == "📚 Browse Subjects":
            await update.message.reply_text(
                "📚 *Select a Subject:*",
                parse_mode='Markdown',
                reply_markup=get_subjects_keyboard()
            )
        elif text == "⚙️ Admin Panel":
            await admin_command(update, context)
        elif text == "ℹ️ Help":
            await help_command(update, context)
        else:
            await update.message.reply_text(
                "Please use the menu buttons or /admin for admin commands."
            )
        return
    
    # Regular users
    db_user = get_user(user.id, user.username, user.first_name, user.last_name)
    
    if db_user.is_blocked:
        await update.message.reply_text("🚫 You are currently blocked. Please try again later.")
        return
    
    text = update.message.text
    
    if text == "📚 Browse Subjects":
        await update.message.reply_text(
            "📚 *Select a Subject:*",
            parse_mode='Markdown',
            reply_markup=get_subjects_keyboard()
        )
    elif text == "ℹ️ Help":
        await help_command(update, context)
    else:
        # Unauthorized message for regular users only
        warnings = add_warning(user.id)
        remaining = config.MAX_WARNINGS - warnings
        
        if remaining > 0:
            await update.message.reply_text(
                f"⚠️ *Warning {warnings}/{config.MAX_WARNINGS}*\n"
                f"Please use the menu buttons only. {remaining} warnings remaining before block.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "🚫 You have been blocked for 24 hours due to multiple warnings. "
                "You will be automatically unblocked after 24 hours."
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    
    data = query.data
    
    # Browse Subjects Flow
    if data.startswith("subject_"):
        subject_code = data.split("_")[1]
        session = Session()
        subject = session.query(Subject).filter_by(code=subject_code).first()
        
        if subject:
            context.user_data['current_subject'] = subject.id
            await query.edit_message_text(
                f"📖 *{subject.name}*\nSelect a chapter:",
                parse_mode='Markdown',
                reply_markup=get_chapters_keyboard(subject.id, "browse")
            )
        session.close()
    
    elif data.startswith("chapter_browse_"):
        chapter_id = int(data.split("_")[2])
        session = Session()
        chapter = session.query(Chapter).get(chapter_id)
        
        if chapter:
            context.user_data['current_chapter'] = chapter_id
            await query.edit_message_text(
                f"📚 *{chapter.name}*\nSelect content type:",
                parse_mode='Markdown',
                reply_markup=get_content_types_keyboard(chapter_id, "browse")
            )
        session.close()
    
    elif data.startswith("content_browse_"):
        _, _, chapter_id, content_type = data.split("_")
        chapter_id = int(chapter_id)
        
        await query.edit_message_text(
            f"Enter content number for {config.CONTENT_TYPES[content_type]}:"
        )
        context.user_data['browse_chapter'] = chapter_id
        context.user_data['browse_content_type'] = content_type
    
    # Admin Flow - Chapter Management
    elif data == "admin_chapters":
        await query.edit_message_text(
            "📖 *Chapter Management*\nSelect a subject:",
            parse_mode='Markdown',
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
                InlineKeyboardButton("➕ Add New Chapter", callback_data="add_new_chapter")
            ])
            
            await query.edit_message_text(
                f"📖 *{subject.name} - Chapters*\nManage chapters:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        session.close()
    
    elif data == "add_new_chapter":
        await query.edit_message_text(
            "✏️ *Add New Chapter*\n\nPlease enter the name of the new chapter:",
            parse_mode='Markdown'
        )
        context.user_data['awaiting_chapter_name'] = True
    
    elif data.startswith("chapter_admin_"):
        chapter_id = int(data.split("_")[2])
        session = Session()
        chapter = session.query(Chapter).get(chapter_id)
        
        if chapter:
            keyboard = [
                [InlineKeyboardButton("🗑️ Delete Chapter", callback_data=f"delete_chapter_{chapter_id}")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"back_to_subject_{chapter.subject.code}")]
            ]
            await query.edit_message_text(
                f"Chapter: *{chapter.name}*\n\nSelect action:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        session.close()
    
    elif data.startswith("delete_chapter_"):
        chapter_id = int(data.split("_")[2])
        session = Session()
        chapter = session.query(Chapter).get(chapter_id)
        
        if chapter:
            chapter_name = chapter.name
            subject_code = chapter.subject.code
            session.delete(chapter)
            session.commit()
            await query.answer(f"✅ Chapter '{chapter_name}' deleted successfully!")
            
            # Go back to subject's chapter list
            subject = session.query(Subject).filter_by(code=subject_code).first()
            if subject:
                keyboard = get_chapters_keyboard(subject.id, "admin")
                keyboard.inline_keyboard.insert(0, [
                    InlineKeyboardButton("➕ Add New Chapter", callback_data="add_new_chapter")
                ])
                
                await query.edit_message_text(
                    f"📖 *{subject.name} - Chapters*\nManage chapters:",
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
        session.close()
    
    # Admin Flow - Add Content
    elif data == "admin_add_content":
        await query.edit_message_text(
            "➕ *Add Content*\nSelect subject:",
            parse_mode='Markdown',
            reply_markup=get_subjects_keyboard()
        )
        context.user_data['admin_mode'] = 'add_content'
    
    # User Management
    elif data == "admin_users":
        session = Session()
        users = session.query(User).order_by(User.created_at.desc()).limit(50).all()
        session.close()
        
        await query.edit_message_text(
            "👥 *User Management*\nSelect a user:",
            parse_mode='Markdown',
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
            await query.edit_message_text(
                user_info,
                parse_mode='Markdown',
                reply_markup=get_user_action_keyboard(user.user_id, user.is_blocked)
            )
    
    elif data.startswith("block_user_"):
        user_id = int(data.split("_")[2])
        block_user(user_id)
        await query.answer("✅ User blocked successfully!")
        await query.edit_message_reply_markup(
            get_user_action_keyboard(user_id, True)
        )
    
    elif data.startswith("unblock_user_"):
        user_id = int(data.split("_")[2])
        unblock_user(user_id)
        await query.answer("✅ User unblocked successfully!")
        await query.edit_message_reply_markup(
            get_user_action_keyboard(user_id, False)
        )
    
    # Navigation
    elif data == "back_to_main":
        await query.edit_message_text(
            "Main Menu",
            reply_markup=get_main_menu_keyboard(is_admin=user.id in config.ADMIN_IDS)
        )
    
    elif data == "back_to_subjects":
        await query.edit_message_text(
            "📚 Select a Subject:",
            parse_mode='Markdown',
            reply_markup=get_subjects_keyboard()
        )
    
    elif data.startswith("back_to_chapters_"):
        chapter_id = int(data.split("_")[3])
        session = Session()
        chapter = session.query(Chapter).get(chapter_id)
        if chapter:
            await query.edit_message_text(
                f"📚 *{chapter.name}*\nSelect content type:",
                parse_mode='Markdown',
                reply_markup=get_content_types_keyboard(chapter_id, "browse")
            )
        session.close()
    
    elif data == "back_to_admin":
        await query.edit_message_text(
            "⚙️ *Admin Panel*\nSelect an option:",
            parse_mode='Markdown',
            reply_markup=get_admin_keyboard()
        )
    
    elif data.startswith("back_to_subject_"):
        subject_code = data.split("_")[3]
        session = Session()
        subject = session.query(Subject).filter_by(code=subject_code).first()
        
        if subject:
            keyboard = get_chapters_keyboard(subject.id, "admin")
            keyboard.inline_keyboard.insert(0, [
                InlineKeyboardButton("➕ Add New Chapter", callback_data="add_new_chapter")
            ])
            
            await query.edit_message_text(
                f"📖 *{subject.name} - Chapters*\nManage chapters:",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
        session.close()

async def handle_chapter_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    # Check if user is admin
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to perform this action.")
        return
    
    # Check if we're awaiting chapter name
    if not context.user_data.get('awaiting_chapter_name'):
        # Check if it's a regular message
        if user.id in config.ADMIN_IDS:
            # Admin can send any message without warnings
            text = update.message.text
            
            if text == "📚 Browse Subjects":
                await update.message.reply_text(
                    "📚 *Select a Subject:*",
                    parse_mode='Markdown',
                    reply_markup=get_subjects_keyboard()
                )
            elif text == "⚙️ Admin Panel":
                await admin_command(update, context)
            elif text == "ℹ️ Help":
                await help_command(update, context)
            else:
                await update.message.reply_text(
                    "Please use the menu buttons or /admin for admin commands."
                )
        return
    
    # Process chapter name
    chapter_name = update.message.text.strip()
    
    if not chapter_name:
        await update.message.reply_text("❌ Chapter name cannot be empty. Please enter a valid name:")
        return
    
    subject_id = context.user_data.get('admin_subject')
    
    if not subject_id:
        await update.message.reply_text("❌ Error: No subject selected. Please start over from admin panel.")
        context.user_data.pop('awaiting_chapter_name', None)
        return
    
    session = Session()
    
    # Check if chapter already exists
    existing = session.query(Chapter).filter_by(
        subject_id=subject_id,
        name=chapter_name
    ).first()
    
    if existing:
        await update.message.reply_text(f"❌ Chapter '{chapter_name}' already exists in this subject!")
        session.close()
        context.user_data.pop('awaiting_chapter_name', None)
        return
    
    # Add new chapter
    new_chapter = Chapter(
        subject_id=subject_id,
        name=chapter_name
    )
    session.add(new_chapter)
    session.commit()
    
    # Get subject for display
    subject = session.query(Subject).get(subject_id)
    session.close()
    
    # Clear the flag
    context.user_data.pop('awaiting_chapter_name', None)
    
    await update.message.reply_text(f"✅ Chapter '{chapter_name}' added to {subject.name} successfully!")
    
    # Show updated chapter list
    keyboard = get_chapters_keyboard(subject_id, "admin")
    keyboard.inline_keyboard.insert(0, [
        InlineKeyboardButton("➕ Add New Chapter", callback_data="add_new_chapter")
    ])
    
    await update.message.reply_text(
        f"📖 *{subject.name} - Chapters*\nManage chapters:",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

async def send_content_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_user(user.id, user.username, user.first_name, user.last_name)
    
    if db_user.is_blocked and user.id not in config.ADMIN_IDS:
        await update.message.reply_text("🚫 You are currently blocked. Please try again later.")
        return
    
    try:
        content_number = int(update.message.text)
        chapter_id = context.user_data.get('browse_chapter')
        content_type = context.user_data.get('browse_content_type')
        
        if not chapter_id or not content_type:
            await update.message.reply_text("❌ Error: Please start over from the beginning.")
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
                        await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=content.file_id,
                            caption=f"🎥 Lecture #{content_number}"
                        )
                    else:
                        await context.bot.send_document(
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
                if content_type == "lecture":
                    with open(content.file_path, 'rb') as file:
                        msg = await context.bot.send_video(
                            chat_id=update.effective_chat.id,
                            video=file,
                            caption=f"🎥 Lecture #{content_number}"
                        )
                        # Save file_id for future use
                        content.file_id = msg.video.file_id
                else:
                    with open(content.file_path, 'rb') as file:
                        msg = await context.bot.send_document(
                            chat_id=update.effective_chat.id,
                            document=file,
                            caption=f"📄 {config.CONTENT_TYPES[content_type]} #{content_number}"
                        )
                        content.file_id = msg.document.file_id
                
                session.commit()
                log_user_action(user.id, f"downloaded_{content_type}_{content_number}")
            else:
                await update.message.reply_text("❌ File not found. Please contact admin.")
        else:
            await update.message.reply_text(f"❌ Content #{content_number} not found for selected type.")
        
        session.close()
        
        # Show subject selection again
        await update.message.reply_text(
            "📚 Select a Subject:",
            reply_markup=get_subjects_keyboard()
        )
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")
        # Don't add warning for admin
        if user.id not in config.ADMIN_IDS:
            add_warning(user.id)

# Admin add content handlers
async def select_subject_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    subject_code = query.data.split("_")[1]
    session = Session()
    subject = session.query(Subject).filter_by(code=subject_code).first()
    
    if subject:
        context.user_data['content_subject'] = subject.id
        context.user_data['admin_mode'] = 'add_content'
        await query.edit_message_text(
            f"➕ *Add Content to {subject.name}*\nSelect chapter:",
            parse_mode='Markdown',
            reply_markup=get_chapters_keyboard(subject.id, "add_content")
        )
    
    session.close()
    return SELECT_SUBJECT_CONTENT

async def select_chapter_content_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chapter_id = int(query.data.split("_")[2])
    context.user_data['content_chapter'] = chapter_id
    
    session = Session()
    chapter = session.query(Chapter).get(chapter_id)
    
    if chapter:
        keyboard = []
        for code, name in config.CONTENT_TYPES.items():
            keyboard.append([InlineKeyboardButton(name, callback_data=f"add_content_type_{chapter_id}_{code}")])
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_add_content")])
        
        await query.edit_message_text(
            f"📚 *{chapter.name}*\nSelect content type:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    session.close()
    return SELECT_CHAPTER_CONTENT

async def select_content_type_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    chapter_id = int(query.data.split("_")[2])
    content_type = query.data.split("_")[3]
    
    context.user_data['content_chapter'] = chapter_id
    context.user_data['content_type'] = content_type
    
    await query.edit_message_text(
        f"Enter content number for {config.CONTENT_TYPES[content_type]}:"
    )
    context.user_data['awaiting_content_number'] = True
    return SELECT_CONTENT_TYPE

async def enter_content_number_admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to perform this action.")
        return SELECT_CONTENT_TYPE
    
    # Check if we're awaiting content number
    if not context.user_data.get('awaiting_content_number'):
        return SELECT_CONTENT_TYPE
    
    try:
        content_number = int(update.message.text)
        context.user_data['content_number'] = content_number
        
        # Clear the flag
        context.user_data.pop('awaiting_content_number', None)
        
        # Check if content already exists
        session = Session()
        existing = session.query(Content).filter_by(
            chapter_id=context.user_data['content_chapter'],
            content_type=context.user_data['content_type'],
            content_number=content_number
        ).first()
        
        if existing:
            await update.message.reply_text("❌ Content with this number already exists!")
            session.close()
            return ConversationHandler.END
        
        session.close()
        
        # Ask for file
        content_type = context.user_data['content_type']
        file_type = "MP4 video" if content_type == "lecture" else "PDF"
        
        await update.message.reply_text(
            f"Please send the {file_type} file for {config.CONTENT_TYPES[content_type]} #{content_number}\n\n"
            f"Format: {'Video (MP4)' if content_type == 'lecture' else 'PDF'}"
        )
        context.user_data['awaiting_content_file'] = True
        return ENTER_CONTENT_NUMBER
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number.")
        return SELECT_CONTENT_TYPE

async def save_content_file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in config.ADMIN_IDS:
        await update.message.reply_text("⛔ You are not authorized to perform this action.")
        return SEND_CONTENT_FILE
    
    # Check if we're awaiting file
    if not context.user_data.get('awaiting_content_file'):
        return SEND_CONTENT_FILE
    
    # Get file
    if update.message.video:
        file = update.message.video
        received_type = "lecture"
    elif update.message.document:
        file = update.message.document
        # Check if it's PDF
        if file.mime_type != "application/pdf":
            await update.message.reply_text("❌ Please send a PDF file for notes/DPP.")
            return SEND_CONTENT_FILE
        received_type = "note" if context.user_data['content_type'] == "note" else "dpp"
    else:
        await update.message.reply_text("❌ Please send a valid file.")
        return SEND_CONTENT_FILE
    
    # Verify file type matches content type
    if context.user_data['content_type'] != received_type:
        await update.message.reply_text(
            f"❌ File type mismatch. Expected {context.user_data['content_type']}, got {received_type}."
        )
        return SEND_CONTENT_FILE
    
    # Save file
    file_path = save_file(
        await file.get_file(),
        context.user_data['content_type'],
        context.user_data['content_chapter'],
        context.user_data['content_number']
    )
    
    if not file_path:
        await update.message.reply_text("❌ Error saving file.")
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
    
    # Clear the flag
    context.user_data.pop('awaiting_content_file', None)
    
    await update.message.reply_text(
        f"✅ {config.CONTENT_TYPES[context.user_data['content_type']]} #{context.user_data['content_number']} added successfully!"
    )
    
    # Return to admin panel
    await update.message.reply_text(
        "⚙️ *Admin Panel*\nSelect an option:",
        parse_mode='Markdown',
        reply_markup=get_admin_keyboard()
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Operation cancelled.",
        reply_markup=get_main_menu_keyboard(is_admin=update.effective_user.id in config.ADMIN_IDS)
    )
    return ConversationHandler.END
