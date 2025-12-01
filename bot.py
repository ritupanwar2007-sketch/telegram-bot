import json
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Updater, CommandHandler, MessageHandler,
    Filters, CallbackQueryHandler, CallbackContext
)

ADMIN_ID = 8064043725
DB_FILE = "database.json"
BOT_TOKEN = "8570013024:AAEBDhWeV4dZJykQsb8IlcK4dK9g0VTUT04"

# Store to track who to notify
user_notifications = set()

def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def clean_chapter_name(chapter):
    """Clean chapter name for callback data"""
    if not chapter:
        return ""
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', chapter)
    cleaned = cleaned.lower().strip().replace(' ', '_')
    return cleaned

def find_original_chapter(subject, chapter_encoded):
    """Find original chapter name from encoded callback name"""
    db = load_db()
    if subject not in db:
        return None
    
    if chapter_encoded in db[subject]:
        return chapter_encoded
    
    for stored_chapter in db[subject].keys():
        if clean_chapter_name(stored_chapter) == chapter_encoded:
            return stored_chapter
    
    for stored_chapter in db[subject].keys():
        if stored_chapter.lower().replace(' ', '_') == chapter_encoded:
            return stored_chapter
    
    return None

def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    user_notifications.add(user_id)
    
    update.message.reply_text(
        "📚 *Board Booster Bot*\n_Created by Vishal_\n\n"
        "✅ You will be notified when new content is uploaded!\n\n"
        "Choose your subject:",
        parse_mode="Markdown",
        reply_markup=subject_keyboard("user")
    )

def admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return update.message.reply_text("❌ Access Denied. Admin only.")
    
    keyboard = [
        [InlineKeyboardButton("📁 Manage Content", callback_data="admin_select_chapter")],
        [InlineKeyboardButton("🗑️ Delete Content", callback_data="admin_delete_mode")],
        [InlineKeyboardButton("➕ Add New Chapter", callback_data="admin_new_chapter")],
        [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
    ]
    
    update.message.reply_text(
        "⚙️ *Admin Panel*\n\nWhat would you like to do?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def out(update: Update, context: CallbackContext):
    """Exit admin panel and clear admin state"""
    if update.message.from_user.id != ADMIN_ID:
        return update.message.reply_text("❌ Access Denied.")
    
    global admin_state
    admin_state.clear()
    
    update.message.reply_text(
        "✅ *Exited Admin Panel*\n\nUse /start to browse content.",
        parse_mode="Markdown"
    )

def broadcast_new_content(context: CallbackContext, subject, chapter, content_type, file_name=None, lecture_no=None):
    """Send notification to all users about new content"""
    if not user_notifications:
        return
    
    content_type_names = {
        "lecture": "🎥 Lecture Video",
        "notes": "📝 Notes PDF", 
        "dpp": "📊 DPP (Practice Problems)"
    }
    
    notification_text = (
        f"📢 *NEW CONTENT UPLOADED!*\n\n"
        f"📘 *Subject:* {subject.capitalize()}\n"
        f"📖 *Chapter:* {chapter}\n"
        f"📁 *Type:* {content_type_names.get(content_type, content_type)}"
    )
    
    if lecture_no and content_type == "lecture":
        notification_text += f"\n🔢 *Lecture No:* {lecture_no}"
    
    notification_text += f"\n📍 *Path:* `/{subject}/{chapter}/{content_type}`"
    
    if file_name:
        notification_text += f"\n📄 *File:* {file_name}"
    
    notification_text += f"\n\n👉 Use /start to access it now!"
    
    for user_id in user_notifications:
        try:
            context.bot.send_message(
                chat_id=user_id,
                text=notification_text,
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"❌ Failed to notify user {user_id}: {e}")
            user_notifications.discard(user_id)

def subject_keyboard(mode, include_back=False, delete_mode=False):
    keyboard = [
        [InlineKeyboardButton("📘 Physics", callback_data=f"{mode}_sub_physics")],
        [InlineKeyboardButton("🧪 Chemistry", callback_data=f"{mode}_sub_chemistry")],
        [InlineKeyboardButton("📐 Maths", callback_data=f"{mode}_sub_maths")],
        [InlineKeyboardButton("📖 English", callback_data=f"{mode}_sub_english")]
    ]
    
    if include_back:
        if delete_mode:
            keyboard.append([InlineKeyboardButton("🔙 Back to Delete Menu", callback_data="back_to_delete_menu")])
        else:
            keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_main")])
    
    return InlineKeyboardMarkup(keyboard)

def get_back_button(back_to, data=None):
    if back_to == "subjects":
        return [InlineKeyboardButton("🔙 Back to Subjects", callback_data="back_subjects")]
    elif back_to == "chapters":
        return [InlineKeyboardButton("🔙 Back to Chapters", callback_data=f"back_chapters_{data}")]
    elif back_to == "types":
        return [InlineKeyboardButton("🔙 Back to Content Types", callback_data=f"back_types_{data}")]
    elif back_to == "admin_main":
        return [InlineKeyboardButton("🔙 Back to Admin Main", callback_data="back_to_admin_main")]
    elif back_to == "lectures":
        return [InlineKeyboardButton("🔙 Back to Lectures", callback_data=f"back_lectures_{data}")]
    elif back_to == "delete_menu":
        return [InlineKeyboardButton("🔙 Back to Delete Menu", callback_data="back_to_delete_menu")]

# Global admin state
admin_state = {}

def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

    print(f"🔍 DEBUG: Callback data received: {data}")

    # ============== BACK BUTTON HANDLERS ==============
    if data == "back_subjects":
        query.edit_message_text(
            "📚 *Choose Subject:*",
            parse_mode="Markdown",
            reply_markup=subject_keyboard("user")
        )
        return
    
    elif data == "back_to_admin_main":
        keyboard = [
            [InlineKeyboardButton("📁 Manage Content", callback_data="admin_select_chapter")],
            [InlineKeyboardButton("🗑️ Delete Content", callback_data="admin_delete_mode")],
            [InlineKeyboardButton("➕ Add New Chapter", callback_data="admin_new_chapter")],
            [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
        ]
        query.edit_message_text(
            "⚙️ *Admin Panel*\n\nWhat would you like to do?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "back_to_delete_menu":
        keyboard = [
            [InlineKeyboardButton("🗑️ Delete Entire Chapter", callback_data="delete_entire_chapter")],
            [InlineKeyboardButton("🗑️ Delete Specific Content", callback_data="delete_specific_content")],
            [InlineKeyboardButton("📊 View Chapter Contents", callback_data="view_chapter_contents")],
            get_back_button("admin_main")
        ]
        query.edit_message_text(
            "🗑️ *Delete Menu*\n\nWhat would you like to delete?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
        
    elif data.startswith("back_chapters_"):
        subject = data.replace("back_chapters_", "")
        db = load_db()
        if subject not in db or not db[subject]:
            query.edit_message_text(
                f"📭 No chapters available for *{subject.capitalize()}*.",
                parse_mode="Markdown"
            )
            return
        chapters = list(db[subject].keys())
        chapters.sort()
        
        keyboard = []
        for ch in chapters:
            display_name = ch
            callback_name = clean_chapter_name(ch)
            keyboard.append([InlineKeyboardButton(f"📖 {display_name}", callback_data=f"user_ch_{subject}_{callback_name}")])
        keyboard.append(get_back_button("subjects"))
        query.edit_message_text(
            f"📂 *{subject.capitalize()} - Select Chapter:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
        
    elif data.startswith("back_types_"):
        parts = data.replace("back_types_", "").split("_")
        if len(parts) >= 2:
            subject = parts[0]
            chapter_encoded = "_".join(parts[1:])
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found in database.")
                return
                
            keyboard = [
                [InlineKeyboardButton("🎥 Lectures", callback_data=f"user_lecture_select_{subject}_{clean_chapter_name(original_chapter)}")],
                [InlineKeyboardButton("📝 Notes", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_notes")],
                [InlineKeyboardButton("📊 DPP", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_dpp")],
            ]
            keyboard.append(get_back_button("chapters", subject))
            query.edit_message_text(
                f"📂 *{original_chapter}*\nSelect content type:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif data.startswith("back_lectures_"):
        parts = data.replace("back_lectures_", "").split("_")
        if len(parts) >= 2:
            subject = parts[0]
            chapter_encoded = "_".join(parts[1:])
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found in database.")
                return
                
            # Show available lecture numbers
            db = load_db()
            lecture_numbers = []
            if subject in db and original_chapter in db[subject] and "lecture" in db[subject][original_chapter]:
                lecture_data = db[subject][original_chapter]["lecture"]
                if isinstance(lecture_data, dict):
                    lecture_numbers = list(lecture_data.keys())
                    lecture_numbers.sort(key=lambda x: int(x) if x.isdigit() else x)
            
            if not lecture_numbers:
                keyboard = [
                    [InlineKeyboardButton("🎥 Lectures", callback_data=f"user_lecture_select_{subject}_{clean_chapter_name(original_chapter)}")],
                    [InlineKeyboardButton("📝 Notes", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_notes")],
                    [InlineKeyboardButton("📊 DPP", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_dpp")],
                ]
                keyboard.append(get_back_button("chapters", subject))
                query.edit_message_text(
                    f"📂 *{original_chapter}*\nSelect content type:",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # Create buttons for lecture numbers
                keyboard = []
                for i in range(0, len(lecture_numbers), 3):
                    row = []
                    for j in range(3):
                        if i + j < len(lecture_numbers):
                            lect_no = lecture_numbers[i + j]
                            row.append(InlineKeyboardButton(f"📹 {lect_no}", 
                                                           callback_data=f"user_lecture_{subject}_{clean_chapter_name(original_chapter)}_{lect_no}"))
                    keyboard.append(row)
                
                keyboard.append(get_back_button("types", f"{subject}_{clean_chapter_name(original_chapter)}"))
                
                query.edit_message_text(
                    f"📹 *{original_chapter} - Lectures*\n\nSelect lecture number:",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        return
    
    # ============== DELETE MODE HANDLERS ==============
    elif data == "admin_delete_mode":
        keyboard = [
            [InlineKeyboardButton("🗑️ Delete Entire Chapter", callback_data="delete_entire_chapter")],
            [InlineKeyboardButton("🗑️ Delete Specific Content", callback_data="delete_specific_content")],
            [InlineKeyboardButton("📊 View Chapter Contents", callback_data="view_chapter_contents")],
            get_back_button("admin_main")
        ]
        query.edit_message_text(
            "🗑️ *Delete Menu*\n\nWhat would you like to delete?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "delete_entire_chapter":
        keyboard = [
            [InlineKeyboardButton("📘 Physics", callback_data="delete_chapter_physics")],
            [InlineKeyboardButton("🧪 Chemistry", callback_data="delete_chapter_chemistry")],
            [InlineKeyboardButton("📐 Maths", callback_data="delete_chapter_maths")],
            [InlineKeyboardButton("📖 English", callback_data="delete_chapter_english")],
            get_back_button("delete_menu")
        ]
        query.edit_message_text(
            "🗑️ *Delete Entire Chapter*\n\nSelect subject:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data.startswith("delete_chapter_"):
        subject = data.replace("delete_chapter_", "")
        db = load_db()
        
        if subject not in db or not db[subject]:
            keyboard = [
                get_back_button("delete_menu")
            ]
            query.edit_message_text(
                f"📭 No chapters exist for *{subject.capitalize()}* to delete.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        chapters = list(db[subject].keys())
        chapters.sort()
        
        # Show chapters for deletion
        keyboard = []
        for ch in chapters:
            # Count content in chapter
            content_count = 0
            if "lecture" in db[subject][ch]:
                if isinstance(db[subject][ch]["lecture"], dict):
                    content_count += len(db[subject][ch]["lecture"])
                else:
                    content_count += 1
            if "notes" in db[subject][ch]:
                content_count += 1
            if "dpp" in db[subject][ch]:
                content_count += 1
            
            keyboard.append([
                InlineKeyboardButton(
                    f"🗑️ {ch} ({content_count} items)", 
                    callback_data=f"confirm_delete_chapter_{subject}_{clean_chapter_name(ch)}"
                )
            ])
        
        keyboard.append(get_back_button("delete_menu"))
        
        query.edit_message_text(
            f"🗑️ *Delete Chapter from {subject.capitalize()}*\n\n"
            f"⚠️ *Warning:* Deleting a chapter will remove ALL its content!\n\n"
            f"Select chapter to delete:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data.startswith("confirm_delete_chapter_"):
        parts = data.replace("confirm_delete_chapter_", "").split("_", 1)
        if len(parts) >= 2:
            subject = parts[0]
            chapter_encoded = parts[1]
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Show confirmation
            keyboard = [
                [InlineKeyboardButton("✅ YES, Delete Entire Chapter", callback_data=f"execute_delete_chapter_{subject}_{clean_chapter_name(original_chapter)}")],
                [InlineKeyboardButton("❌ NO, Cancel", callback_data=f"delete_chapter_{subject}")]
            ]
            
            db = load_db()
            content_summary = []
            if subject in db and original_chapter in db[subject]:
                if "lecture" in db[subject][original_chapter]:
                    if isinstance(db[subject][original_chapter]["lecture"], dict):
                        lect_count = len(db[subject][original_chapter]["lecture"])
                        content_summary.append(f"{lect_count} lecture(s)")
                    else:
                        content_summary.append("1 lecture")
                if "notes" in db[subject][original_chapter]:
                    content_summary.append("notes")
                if "dpp" in db[subject][original_chapter]:
                    content_summary.append("DPP")
            
            content_text = ", ".join(content_summary) if content_summary else "no content"
            
            query.edit_message_text(
                f"⚠️ *CONFIRM DELETION*\n\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {original_chapter}\n\n"
                f"📦 *Will delete:* {content_text}\n\n"
                f"❌ *This action cannot be undone!*\n\n"
                f"Are you sure you want to delete this entire chapter?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif data.startswith("execute_delete_chapter_"):
        parts = data.replace("execute_delete_chapter_", "").split("_", 1)
        if len(parts) >= 2:
            subject = parts[0]
            chapter_encoded = parts[1]
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Delete the chapter
            db = load_db()
            if subject in db and original_chapter in db[subject]:
                deleted_items = []
                if "lecture" in db[subject][original_chapter]:
                    if isinstance(db[subject][original_chapter]["lecture"], dict):
                        lect_count = len(db[subject][original_chapter]["lecture"])
                        deleted_items.append(f"{lect_count} lectures")
                    else:
                        deleted_items.append("1 lecture")
                if "notes" in db[subject][original_chapter]:
                    deleted_items.append("notes")
                if "dpp" in db[subject][original_chapter]:
                    deleted_items.append("DPP")
                
                del db[subject][original_chapter]
                
                # Remove subject if empty
                if not db[subject]:
                    del db[subject]
                
                save_db(db)
                
                deleted_text = ", ".join(deleted_items) if deleted_items else "empty chapter"
                
                query.edit_message_text(
                    f"✅ *Chapter Deleted Successfully!*\n\n"
                    f"📘 *Subject:* {subject.capitalize()}\n"
                    f"📖 *Chapter:* {original_chapter}\n\n"
                    f"🗑️ *Deleted:* {deleted_text}\n\n"
                    f"Users will no longer see this chapter.",
                    parse_mode="Markdown"
                )
            else:
                query.edit_message_text("❌ Chapter not found in database.")
        
        # Return to delete menu
        keyboard = [
            [InlineKeyboardButton("🗑️ Delete Entire Chapter", callback_data="delete_entire_chapter")],
            [InlineKeyboardButton("🗑️ Delete Specific Content", callback_data="delete_specific_content")],
            [InlineKeyboardButton("📊 View Chapter Contents", callback_data="view_chapter_contents")],
            get_back_button("admin_main")
        ]
        query.message.reply_text(
            "🗑️ *Delete Menu*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "delete_specific_content":
        keyboard = [
            [InlineKeyboardButton("📘 Physics", callback_data="delete_content_physics")],
            [InlineKeyboardButton("🧪 Chemistry", callback_data="delete_content_chemistry")],
            [InlineKeyboardButton("📐 Maths", callback_data="delete_content_maths")],
            [InlineKeyboardButton("📖 English", callback_data="delete_content_english")],
            get_back_button("delete_menu")
        ]
        query.edit_message_text(
            "🗑️ *Delete Specific Content*\n\nSelect subject:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data.startswith("delete_content_"):
        subject = data.replace("delete_content_", "")
        db = load_db()
        
        if subject not in db or not db[subject]:
            keyboard = [
                get_back_button("delete_menu")
            ]
            query.edit_message_text(
                f"📭 No chapters exist for *{subject.capitalize()}*.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        chapters = list(db[subject].keys())
        chapters.sort()
        
        # Show chapters for content deletion
        keyboard = []
        for ch in chapters:
            keyboard.append([
                InlineKeyboardButton(
                    f"📖 {ch}", 
                    callback_data=f"select_chapter_content_{subject}_{clean_chapter_name(ch)}"
                )
            ])
        
        keyboard.append(get_back_button("delete_menu"))
        
        query.edit_message_text(
            f"🗑️ *Delete Content from {subject.capitalize()}*\n\n"
            f"Select chapter to delete content from:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data.startswith("select_chapter_content_"):
        parts = data.replace("select_chapter_content_", "").split("_", 1)
        if len(parts) >= 2:
            subject = parts[0]
            chapter_encoded = parts[1]
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Show content options for deletion
            db = load_db()
            keyboard = []
            
            if subject in db and original_chapter in db[subject]:
                # Lectures
                if "lecture" in db[subject][original_chapter]:
                    if isinstance(db[subject][original_chapter]["lecture"], dict):
                        lect_count = len(db[subject][original_chapter]["lecture"])
                        keyboard.append([
                            InlineKeyboardButton(
                                f"🗑️ Delete All Lectures ({lect_count})", 
                                callback_data=f"delete_all_lectures_{subject}_{clean_chapter_name(original_chapter)}"
                            )
                        ])
                        # Individual lecture numbers
                        lecture_numbers = list(db[subject][original_chapter]["lecture"].keys())
                        lecture_numbers.sort(key=lambda x: int(x) if x.isdigit() else x)
                        for lect_no in lecture_numbers:
                            keyboard.append([
                                InlineKeyboardButton(
                                    f"🗑️ Delete Lecture {lect_no}", 
                                    callback_data=f"delete_lecture_{subject}_{clean_chapter_name(original_chapter)}_{lect_no}"
                                )
                            ])
                    else:
                        keyboard.append([
                            InlineKeyboardButton(
                                f"🗑️ Delete Lecture", 
                                callback_data=f"delete_lecture_{subject}_{clean_chapter_name(original_chapter)}_1"
                            )
                        ])
                
                # Notes
                if "notes" in db[subject][original_chapter]:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🗑️ Delete Notes", 
                            callback_data=f"delete_content_{subject}_{clean_chapter_name(original_chapter)}_notes"
                        )
                    ])
                
                # DPP
                if "dpp" in db[subject][original_chapter]:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🗑️ Delete DPP", 
                            callback_data=f"delete_content_{subject}_{clean_chapter_name(original_chapter)}_dpp"
                        )
                    ])
            
            if not keyboard:
                keyboard.append([InlineKeyboardButton("📭 No content to delete", callback_data="none")])
            
            keyboard.append(get_back_button("delete_menu"))
            
            query.edit_message_text(
                f"🗑️ *Delete Content from:*\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {original_chapter}\n\n"
                f"Select content to delete:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif data.startswith("delete_all_lectures_"):
        parts = data.replace("delete_all_lectures_", "").split("_", 1)
        if len(parts) >= 2:
            subject = parts[0]
            chapter_encoded = parts[1]
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Confirm deletion of all lectures
            db = load_db()
            lect_count = 0
            if subject in db and original_chapter in db[subject] and "lecture" in db[subject][original_chapter]:
                if isinstance(db[subject][original_chapter]["lecture"], dict):
                    lect_count = len(db[subject][original_chapter]["lecture"])
            
            keyboard = [
                [InlineKeyboardButton("✅ YES, Delete All Lectures", callback_data=f"execute_delete_all_lectures_{subject}_{clean_chapter_name(original_chapter)}")],
                [InlineKeyboardButton("❌ NO, Cancel", callback_data=f"select_chapter_content_{subject}_{clean_chapter_name(original_chapter)}")]
            ]
            
            query.edit_message_text(
                f"⚠️ *CONFIRM DELETION*\n\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {original_chapter}\n\n"
                f"🗑️ *Will delete:* All {lect_count} lectures\n\n"
                f"❌ *This action cannot be undone!*\n\n"
                f"Are you sure you want to delete all lectures?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif data.startswith("execute_delete_all_lectures_"):
        parts = data.replace("execute_delete_all_lectures_", "").split("_", 1)
        if len(parts) >= 2:
            subject = parts[0]
            chapter_encoded = parts[1]
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Delete all lectures
            db = load_db()
            if subject in db and original_chapter in db[subject] and "lecture" in db[subject][original_chapter]:
                lect_count = 0
                if isinstance(db[subject][original_chapter]["lecture"], dict):
                    lect_count = len(db[subject][original_chapter]["lecture"])
                
                del db[subject][original_chapter]["lecture"]
                save_db(db)
                
                query.edit_message_text(
                    f"✅ *Deleted All Lectures Successfully!*\n\n"
                    f"📘 *Subject:* {subject.capitalize()}\n"
                    f"📖 *Chapter:* {original_chapter}\n\n"
                    f"🗑️ *Deleted:* {lect_count} lectures\n\n"
                    f"Users will no longer see these lectures.",
                    parse_mode="Markdown"
                )
            else:
                query.edit_message_text("❌ No lectures found to delete.")
        
        # Return to content selection
        keyboard = [
            [InlineKeyboardButton("📊 View Chapter Contents", callback_data=f"view_chapter_{subject}_{clean_chapter_name(original_chapter)}")],
            get_back_button("delete_menu")
        ]
        query.message.reply_text(
            "What would you like to do next?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data.startswith("delete_lecture_"):
        parts = data.split("_")
        if len(parts) >= 5:
            subject = parts[2]
            chapter_encoded = parts[3]
            lecture_no = parts[4]
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Confirm deletion of specific lecture
            keyboard = [
                [InlineKeyboardButton("✅ YES, Delete Lecture", callback_data=f"execute_delete_lecture_{subject}_{clean_chapter_name(original_chapter)}_{lecture_no}")],
                [InlineKeyboardButton("❌ NO, Cancel", callback_data=f"select_chapter_content_{subject}_{clean_chapter_name(original_chapter)}")]
            ]
            
            query.edit_message_text(
                f"⚠️ *CONFIRM DELETION*\n\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {original_chapter}\n"
                f"📹 *Lecture No:* {lecture_no}\n\n"
                f"❌ *This action cannot be undone!*\n\n"
                f"Are you sure you want to delete this lecture?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif data.startswith("execute_delete_lecture_"):
        parts = data.split("_")
        if len(parts) >= 6:
            subject = parts[3]
            chapter_encoded = parts[4]
            lecture_no = parts[5]
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Delete specific lecture
            db = load_db()
            if (subject in db and 
                original_chapter in db[subject] and 
                "lecture" in db[subject][original_chapter] and
                isinstance(db[subject][original_chapter]["lecture"], dict) and
                lecture_no in db[subject][original_chapter]["lecture"]):
                
                del db[subject][original_chapter]["lecture"][lecture_no]
                
                # If no lectures left, remove lecture key
                if not db[subject][original_chapter]["lecture"]:
                    del db[subject][original_chapter]["lecture"]
                
                save_db(db)
                
                query.edit_message_text(
                    f"✅ *Lecture Deleted Successfully!*\n\n"
                    f"📘 *Subject:* {subject.capitalize()}\n"
                    f"📖 *Chapter:* {original_chapter}\n"
                    f"📹 *Lecture No:* {lecture_no}\n\n"
                    f"Users will no longer see this lecture.",
                    parse_mode="Markdown"
                )
            else:
                query.edit_message_text("❌ Lecture not found.")
        
        # Return to content selection
        keyboard = [
            [InlineKeyboardButton("📊 View Chapter Contents", callback_data=f"view_chapter_{subject}_{clean_chapter_name(original_chapter)}")],
            get_back_button("delete_menu")
        ]
        query.message.reply_text(
            "What would you like to do next?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data.startswith("delete_content_"):
        # Handle notes and DPP deletion (not lectures)
        parts = data.split("_")
        if len(parts) >= 5:
            subject = parts[2]
            chapter_encoded = parts[3]
            content_type = parts[4]  # notes or dpp
            
            if content_type == "lecture":
                return  # Handled separately
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            content_type_names = {
                "notes": "Notes",
                "dpp": "DPP"
            }
            
            # Confirm deletion
            keyboard = [
                [InlineKeyboardButton(f"✅ YES, Delete {content_type_names.get(content_type, content_type)}", 
                                     callback_data=f"execute_delete_{content_type}_{subject}_{clean_chapter_name(original_chapter)}")],
                [InlineKeyboardButton("❌ NO, Cancel", callback_data=f"select_chapter_content_{subject}_{clean_chapter_name(original_chapter)}")]
            ]
            
            query.edit_message_text(
                f"⚠️ *CONFIRM DELETION*\n\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {original_chapter}\n"
                f"📁 *Type:* {content_type_names.get(content_type, content_type)}\n\n"
                f"❌ *This action cannot be undone!*\n\n"
                f"Are you sure you want to delete this content?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif data.startswith("execute_delete_notes_") or data.startswith("execute_delete_dpp_"):
        parts = data.split("_")
        if len(parts) >= 5:
            content_type = parts[2]  # notes or dpp
            subject = parts[3]
            chapter_encoded = parts[4]
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Delete the content
            db = load_db()
            if subject in db and original_chapter in db[subject] and content_type in db[subject][original_chapter]:
                del db[subject][original_chapter][content_type]
                save_db(db)
                
                content_type_names = {
                    "notes": "Notes",
                    "dpp": "DPP"
                }
                
                query.edit_message_text(
                    f"✅ *{content_type_names.get(content_type, content_type)} Deleted Successfully!*\n\n"
                    f"📘 *Subject:* {subject.capitalize()}\n"
                    f"📖 *Chapter:* {original_chapter}\n"
                    f"📁 *Type:* {content_type_names.get(content_type, content_type)}\n\n"
                    f"Users will no longer see this content.",
                    parse_mode="Markdown"
                )
            else:
                query.edit_message_text(f"❌ {content_type.capitalize()} not found.")
        
        # Return to content selection
        keyboard = [
            [InlineKeyboardButton("📊 View Chapter Contents", callback_data=f"view_chapter_{subject}_{clean_chapter_name(original_chapter)}")],
            get_back_button("delete_menu")
        ]
        query.message.reply_text(
            "What would you like to do next?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "view_chapter_contents":
        keyboard = [
            [InlineKeyboardButton("📘 Physics", callback_data="view_contents_physics")],
            [InlineKeyboardButton("🧪 Chemistry", callback_data="view_contents_chemistry")],
            [InlineKeyboardButton("📐 Maths", callback_data="view_contents_maths")],
            [InlineKeyboardButton("📖 English", callback_data="view_contents_english")],
            get_back_button("delete_menu")
        ]
        query.edit_message_text(
            "📊 *View Chapter Contents*\n\nSelect subject:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data.startswith("view_contents_"):
        subject = data.replace("view_contents_", "")
        db = load_db()
        
        if subject not in db or not db[subject]:
            keyboard = [
                get_back_button("delete_menu")
            ]
            query.edit_message_text(
                f"📭 No chapters exist for *{subject.capitalize()}*.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        chapters = list(db[subject].keys())
        chapters.sort()
        
        # Show chapters for viewing
        keyboard = []
        for ch in chapters:
            keyboard.append([
                InlineKeyboardButton(
                    f"📖 {ch}", 
                    callback_data=f"view_chapter_{subject}_{clean_chapter_name(ch)}"
                )
            ])
        
        keyboard.append(get_back_button("delete_menu"))
        
        query.edit_message_text(
            f"📊 *View Contents of {subject.capitalize()}*\n\n"
            f"Select chapter to view contents:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data.startswith("view_chapter_"):
        parts = data.replace("view_chapter_", "").split("_", 1)
        if len(parts) >= 2:
            subject = parts[0]
            chapter_encoded = parts[1]
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Show chapter contents
            db = load_db()
            content_text = f"📊 *Chapter Contents*\n\n"
            content_text += f"📘 *Subject:* {subject.capitalize()}\n"
            content_text += f"📖 *Chapter:* {original_chapter}\n\n"
            
            if subject in db and original_chapter in db[subject]:
                # Lectures
                if "lecture" in db[subject][original_chapter]:
                    if isinstance(db[subject][original_chapter]["lecture"], dict):
                        lecture_numbers = list(db[subject][original_chapter]["lecture"].keys())
                        lecture_numbers.sort(key=lambda x: int(x) if x.isdigit() else x)
                        content_text += f"🎥 *Lectures:* {len(lecture_numbers)} lectures\n"
                        content_text += f"   Numbers: {', '.join(lecture_numbers)}\n"
                    else:
                        content_text += "🎥 *Lectures:* 1 lecture\n"
                
                # Notes
                if "notes" in db[subject][original_chapter]:
                    content_text += "📝 *Notes:* Available ✅\n"
                else:
                    content_text += "📝 *Notes:* Not available ❌\n"
                
                # DPP
                if "dpp" in db[subject][original_chapter]:
                    content_text += "📊 *DPP:* Available ✅\n"
                else:
                    content_text += "📊 *DPP:* Not available ❌\n"
            else:
                content_text += "📭 *No content available*\n"
            
            keyboard = [
                [InlineKeyboardButton("🗑️ Delete Content from This Chapter", callback_data=f"select_chapter_content_{subject}_{clean_chapter_name(original_chapter)}")],
                get_back_button("delete_menu")
            ]
            
            query.edit_message_text(
                content_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # ============== ADMIN CONTENT MANAGEMENT ==============
    elif data == "admin_select_chapter":
        keyboard = [
            [InlineKeyboardButton("📘 Physics", callback_data="admin_existing_physics")],
            [InlineKeyboardButton("🧪 Chemistry", callback_data="admin_existing_chemistry")],
            [InlineKeyboardButton("📐 Maths", callback_data="admin_existing_maths")],
            [InlineKeyboardButton("📖 English", callback_data="admin_existing_english")],
            get_back_button("admin_main")
        ]
        query.edit_message_text(
            "📚 *Select Subject with Existing Chapters:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "admin_new_chapter":
        keyboard = [
            [InlineKeyboardButton("📘 Physics", callback_data="admin_new_physics")],
            [InlineKeyboardButton("🧪 Chemistry", callback_data="admin_new_chemistry")],
            [InlineKeyboardButton("📐 Maths", callback_data="admin_new_maths")],
            [InlineKeyboardButton("📖 English", callback_data="admin_new_english")],
            get_back_button("admin_main")
        ]
        query.edit_message_text(
            "📚 *Select Subject for NEW Chapter:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Handle selecting existing chapters for a subject
    elif data.startswith("admin_existing_"):
        subject = data.replace("admin_existing_", "")
        db = load_db()
        
        if subject not in db or not db[subject]:
            keyboard = [
                [InlineKeyboardButton("➕ Add New Chapter Instead", callback_data=f"admin_new_{subject}")],
                get_back_button("admin_main")
            ]
            query.edit_message_text(
                f"📭 No chapters exist for *{subject.capitalize()}* yet.\n\nWould you like to add a new chapter?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        chapters = list(db[subject].keys())
        chapters.sort()
        
        # Show existing chapters for selection
        keyboard = []
        for ch in chapters:
            # Show what content types are already available
            content_types = []
            if "lecture" in db[subject][ch]:
                if isinstance(db[subject][ch]["lecture"], dict):
                    lect_count = len(db[subject][ch]["lecture"])
                    content_types.append(f"🎥{lect_count}")
                else:
                    content_types.append("🎥")
            if "notes" in db[subject][ch]:
                content_types.append("📝")
            if "dpp" in db[subject][ch]:
                content_types.append("📊")
            
            content_status = " ".join(content_types) if content_types else "📭"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{content_status} {ch}", 
                    callback_data=f"admin_edit_{subject}_{clean_chapter_name(ch)}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton("➕ Add New Chapter to This Subject", callback_data=f"admin_new_{subject}")])
        keyboard.append(get_back_button("admin_main"))
        
        query.edit_message_text(
            f"📂 *{subject.capitalize()} - Existing Chapters:*\n\n"
            f"🎥 = Lecture(s)  📝 = Notes  📊 = DPP  📭 = No content\n\n"
            f"Select a chapter to add more content:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Handle selecting a specific chapter to edit
    elif data.startswith("admin_edit_"):
        parts = data.split("_", 2)
        if len(parts) >= 3:
            subject = parts[1]
            chapter_encoded = parts[2]
            
            # Find original chapter name
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            admin_state["subject"] = subject
            admin_state["chapter"] = original_chapter
            admin_state["step"] = "type"
            
            # Show content type selection for this chapter
            keyboard = [
                [InlineKeyboardButton("🎥 Lecture (MP4)", callback_data="admin_lecture_type")],
                [InlineKeyboardButton("📝 Notes (PDF)", callback_data="admin_type_notes")],
                [InlineKeyboardButton("📊 DPP (PDF)", callback_data="admin_type_dpp")],
                get_back_button("admin_main")
            ]
            
            # Show what's already uploaded
            db = load_db()
            existing_content = []
            if subject in db and original_chapter in db[subject]:
                if "lecture" in db[subject][original_chapter]:
                    if isinstance(db[subject][original_chapter]["lecture"], dict):
                        lect_count = len(db[subject][original_chapter]["lecture"])
                        existing_content.append(f"🎥 {lect_count} Lectures")
                    else:
                        existing_content.append("🎥 Lecture")
                if "notes" in db[subject][original_chapter]:
                    existing_content.append("📝 Notes")
                if "dpp" in db[subject][original_chapter]:
                    existing_content.append("📊 DPP")
            
            status_text = ""
            if existing_content:
                status_text = f"\n\n✅ *Already uploaded:* {', '.join(existing_content)}"
            
            query.edit_message_text(
                f"📝 *Adding content to:*\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {original_chapter}\n\n"
                f"Select content type to upload:{status_text}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    # Handle lecture type selection
    elif data == "admin_lecture_type":
        admin_state["step"] = "lecture_no"
        
        subject = admin_state.get("subject", "Unknown")
        chapter = admin_state.get("chapter", "Unknown")
        
        # Check if lectures already exist
        db = load_db()
        existing_lectures = []
        if subject in db and chapter in db[subject] and "lecture" in db[subject][chapter]:
            if isinstance(db[subject][chapter]["lecture"], dict):
                existing_lectures = list(db[subject][chapter]["lecture"].keys())
                existing_lectures.sort(key=lambda x: int(x) if x.isdigit() else x)
        
        keyboard = []
        if existing_lectures:
            keyboard.append([InlineKeyboardButton("➕ Add New Lecture Number", callback_data="admin_new_lecture_no")])
            
            # Show existing lecture numbers as options
            for i in range(0, len(existing_lectures), 3):
                row = []
                for j in range(3):
                    if i + j < len(existing_lectures):
                        lect_no = existing_lectures[i + j]
                        row.append(InlineKeyboardButton(f"📹 {lect_no}", 
                                                       callback_data=f"admin_lecture_no_{lect_no}"))
                if row:
                    keyboard.append(row)
        else:
            keyboard.append([InlineKeyboardButton("📹 Lecture 1", callback_data="admin_new_lecture_no")])
        
        keyboard.append(get_back_button("admin_main"))
        
        status_text = ""
        if existing_lectures:
            status_text = f"\n\n📹 *Existing lectures:* {', '.join(existing_lectures)}"
        
        query.edit_message_text(
            f"📝 *Adding Lecture to:*\n"
            f"📘 *Subject:* {subject.capitalize()}\n"
            f"📖 *Chapter:* {chapter}\n\n"
            f"Select lecture number or add new:{status_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Handle selecting existing lecture number
    elif data.startswith("admin_lecture_no_"):
        lecture_no = data.replace("admin_lecture_no_", "")
        admin_state["lecture_no"] = lecture_no
        admin_state["step"] = "upload"
        admin_state["ctype"] = "lecture"
        
        subject = admin_state.get("subject", "Unknown")
        chapter = admin_state.get("chapter", "Unknown")
        
        keyboard = [
            get_back_button("admin_main"),
            [InlineKeyboardButton("❌ Cancel & Exit", callback_data="exit_admin_mode")]
        ]
        
        query.edit_message_text(
            f"⬆️ *Uploading Lecture {lecture_no} to:*\n"
            f"📘 *Subject:* {subject.capitalize()}\n"
            f"📖 *Chapter:* {chapter}\n\n"
            f"*This will replace existing Lecture {lecture_no}*\n\n"
            f"Please send the video file now:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Handle new lecture number
    elif data == "admin_new_lecture_no":
        admin_state["step"] = "ask_lecture_no"
        
        subject = admin_state.get("subject", "Unknown")
        chapter = admin_state.get("chapter", "Unknown")
        
        keyboard = [
            get_back_button("admin_main"),
            [InlineKeyboardButton("❌ Cancel & Exit", callback_data="exit_admin_mode")]
        ]
        
        # Check existing lectures to suggest next number
        db = load_db()
        next_lecture_no = 1
        if subject in db and chapter in db[subject] and "lecture" in db[subject][chapter]:
            if isinstance(db[subject][chapter]["lecture"], dict):
                existing_nums = [int(n) for n in db[subject][chapter]["lecture"].keys() if n.isdigit()]
                if existing_nums:
                    next_lecture_no = max(existing_nums) + 1
        
        query.edit_message_text(
            f"📝 *Adding NEW Lecture to:*\n"
            f"📘 *Subject:* {subject.capitalize()}\n"
            f"📖 *Chapter:* {chapter}\n\n"
            f"Enter the lecture number (e.g., {next_lecture_no}):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Handle new chapter selection
    elif data.startswith("admin_new_"):
        subject = data.replace("admin_new_", "")
        admin_state["subject"] = subject
        admin_state["step"] = "chapter"
        
        keyboard = [
            get_back_button("admin_main"),
            [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
        ]
        query.edit_message_text(
            f"📘 *{subject.capitalize()} Selected for NEW Chapter*\n\n"
            f"📝 Please send the *new chapter name*:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Exit admin mode from callback
    if data == "exit_admin_mode":
        admin_state.clear()
        query.edit_message_text(
            "✅ *Exited Admin Mode*\n\nUse /start to browse content.",
            parse_mode="Markdown"
        )
        return

    # ============== USER CONTENT ACCESS ==============
    # User selects lectures - show lecture numbers
    elif data.startswith("user_lecture_select_"):
        parts = data.replace("user_lecture_select_", "").split("_")
        if len(parts) >= 2:
            subject = parts[0]
            chapter_encoded = "_".join(parts[1:])
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Get available lecture numbers
            db = load_db()
            lecture_numbers = []
            if subject in db and original_chapter in db[subject] and "lecture" in db[subject][original_chapter]:
                lecture_data = db[subject][original_chapter]["lecture"]
                if isinstance(lecture_data, dict):
                    lecture_numbers = list(lecture_data.keys())
                    lecture_numbers.sort(key=lambda x: int(x) if x.isdigit() else x)
            
            if not lecture_numbers:
                keyboard = [
                    [InlineKeyboardButton("🎥 Lectures", callback_data=f"user_lecture_select_{subject}_{clean_chapter_name(original_chapter)}")],
                    [InlineKeyboardButton("📝 Notes", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_notes")],
                    [InlineKeyboardButton("📊 DPP", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_dpp")],
                ]
                keyboard.append(get_back_button("chapters", subject))
                query.edit_message_text(
                    f"📭 No lectures available for *{original_chapter}* yet.\n\nPlease select another content type:",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            # Create buttons for lecture numbers (3 per row)
            keyboard = []
            for i in range(0, len(lecture_numbers), 3):
                row = []
                for j in range(3):
                    if i + j < len(lecture_numbers):
                        lect_no = lecture_numbers[i + j]
                        row.append(InlineKeyboardButton(f"📹 {lect_no}", 
                                                       callback_data=f"user_lecture_{subject}_{clean_chapter_name(original_chapter)}_{lect_no}"))
                if row:
                    keyboard.append(row)
            
            keyboard.append(get_back_button("types", f"{subject}_{clean_chapter_name(original_chapter)}"))
            
            query.edit_message_text(
                f"📹 *{original_chapter} - Lectures*\n\nSelect lecture number:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    # User selects specific lecture number
    elif data.startswith("user_lecture_"):
        parts = data.split("_")
        if len(parts) >= 5:
            subject = parts[2]
            chapter_encoded = parts[3]
            lecture_no = parts[4]
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                query.edit_message_text("❌ Chapter not found.")
                return
            
            # Get the specific lecture file
            db = load_db()
            file_id = None
            if (subject in db and 
                original_chapter in db[subject] and 
                "lecture" in db[subject][original_chapter] and
                isinstance(db[subject][original_chapter]["lecture"], dict) and
                lecture_no in db[subject][original_chapter]["lecture"]):
                
                file_id = db[subject][original_chapter]["lecture"][lecture_no]
            
            if not file_id:
                # Go back to lecture selection
                keyboard = []
                if subject in db and original_chapter in db[subject] and "lecture" in db[subject][original_chapter]:
                    if isinstance(db[subject][original_chapter]["lecture"], dict):
                        lecture_numbers = list(db[subject][original_chapter]["lecture"].keys())
                        lecture_numbers.sort(key=lambda x: int(x) if x.isdigit() else x)
                        
                        for i in range(0, len(lecture_numbers), 3):
                            row = []
                            for j in range(3):
                                if i + j < len(lecture_numbers):
                                    lect_no = lecture_numbers[i + j]
                                    row.append(InlineKeyboardButton(f"📹 {lect_no}", 
                                                                   callback_data=f"user_lecture_{subject}_{clean_chapter_name(original_chapter)}_{lect_no}"))
                            if row:
                                keyboard.append(row)
                
                keyboard.append(get_back_button("types", f"{subject}_{clean_chapter_name(original_chapter)}"))
                
                query.edit_message_text(
                    f"❌ *Lecture {lecture_no} not found* for *{original_chapter}*.\n\nSelect another lecture:",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            # Send the lecture video
            try:
                context.bot.send_video(
                    chat_id=query.message.chat_id,
                    video=file_id,
                    caption=f"📹 *{original_chapter} - Lecture {lecture_no}*\n\n_Enjoy your study!_ 📚",
                    parse_mode="Markdown"
                )
                
                # Send navigation options
                keyboard = [
                    get_back_button("lectures", f"{subject}_{clean_chapter_name(original_chapter)}"),
                    get_back_button("subjects")
                ]
                query.message.reply_text(
                    "✅ *Lecture Sent Successfully!*\n\nWhat would you like to do next?",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            except Exception as e:
                print(f"❌ ERROR sending lecture: {str(e)}")
                query.edit_message_text(
                    f"❌ *Error*\n\nFailed to send lecture. Please try again later.",
                    parse_mode="Markdown"
                )
        return
    
    # User content type selection (for notes and DPP)
    elif data.startswith("user_type_"):
        try:
            parts = data.split("_")
            if len(parts) >= 5:
                subject = parts[2]
                chapter_encoded = parts[3]
                ctype = parts[4]
                
                # Skip if it's lecture (handled separately)
                if ctype == "lecture":
                    return
                
                print(f"🔍 DEBUG: user_type_ parsed - subject: {subject}, chapter_encoded: {chapter_encoded}, type: {ctype}")
                
                original_chapter = find_original_chapter(subject, chapter_encoded)
                
                if not original_chapter:
                    query.edit_message_text("❌ Chapter not found.")
                    return
                
                db = load_db()
                file_id = None
                if subject in db and original_chapter in db[subject]:
                    file_id = db[subject][original_chapter].get(ctype)
                
                if not file_id:
                    keyboard = [
                        [InlineKeyboardButton("🎥 Lectures", callback_data=f"user_lecture_select_{subject}_{clean_chapter_name(original_chapter)}")],
                        [InlineKeyboardButton("📝 Notes", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_notes")],
                        [InlineKeyboardButton("📊 DPP", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_dpp")],
                    ]
                    keyboard.append(get_back_button("chapters", subject))
                    
                    content_type_names = {
                        "lecture": "Lecture Video",
                        "notes": "Notes PDF",
                        "dpp": "DPP (Daily Practice Problems)"
                    }
                    
                    query.edit_message_text(
                        f"⚠️ *Content Not Available*\n\n{content_type_names.get(ctype, ctype)} for *{original_chapter}* is not uploaded yet.\n\nPlease select another content type:",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    return
                
                try:
                    doc_type = "Notes" if ctype == "notes" else "DPP"
                    context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=file_id,
                        caption=f"📄 *{original_chapter} - {doc_type}*\n\n_Happy Learning!_ ✨",
                        parse_mode="Markdown"
                    )
                    
                    keyboard = [
                        get_back_button("types", f"{subject}_{clean_chapter_name(original_chapter)}"),
                        get_back_button("subjects")
                    ]
                    query.message.reply_text(
                        "✅ *Content Sent Successfully!*\n\nWhat would you like to do next?",
                        parse_mode="Markdown",
                        reply_markup=InlineKeyboardMarkup(keyboard)
                    )
                    
                except Exception as e:
                    print(f"❌ ERROR sending file: {str(e)}")
                    query.edit_message_text(
                        f"❌ *Error*\n\nFailed to send content. Please try again later.",
                        parse_mode="Markdown"
                    )
        except Exception as e:
            print(f"❌ ERROR in user_type_: {str(e)}")
            query.edit_message_text(
                "❌ Error processing your request. Please try again.",
                parse_mode="Markdown"
            )
        return

def admin_type(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()
    
    if data == "admin_type_notes":
        admin_state["ctype"] = "notes"
        admin_state["step"] = "upload"
        show_upload_prompt(query, "Notes PDF (PDF)")
        
    elif data == "admin_type_dpp":
        admin_state["ctype"] = "dpp"
        admin_state["step"] = "upload"
        show_upload_prompt(query, "DPP PDF (PDF)")

def show_upload_prompt(query, content_type_name):
    subject = admin_state.get("subject", "Unknown")
    chapter = admin_state.get("chapter", "Unknown")
    
    keyboard = [
        get_back_button("admin_main"),
        [InlineKeyboardButton("❌ Cancel & Exit", callback_data="exit_admin_mode")]
    ]
    
    query.edit_message_text(
        f"⬆️ *Uploading to:*\n"
        f"📘 *Subject:* {subject.capitalize()}\n"
        f"📖 *Chapter:* {chapter}\n\n"
        f"*Upload {content_type_name}:*\n\nPlease send the file now:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def message_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    
    # Handle non-admin users
    if user_id != ADMIN_ID:
        if update.message.text and update.message.text.startswith('/'):
            return
        
        update.message.reply_text(
            "⚠️ *Stay Focused on Your Studies!*\n\n"
            "Use */start* to access study materials.\n\n"
            "📚 *You can also visit our website:*\n"
            "🌐 www.setugyan.live\n\n"
            "_Stop wasting time on unnecessary messages._",
            parse_mode="Markdown",
            disable_web_page_preview=False
        )
        return
    
    # ADMIN HANDLING
    if admin_state.get("step") == "chapter":
        chapter_name = update.message.text.strip()
        if not chapter_name:
            update.message.reply_text("❌ Please enter a valid chapter name.")
            return
            
        admin_state["chapter"] = chapter_name
        admin_state["step"] = "type"
        
        keyboard = [
            [InlineKeyboardButton("🎥 Lecture (MP4)", callback_data="admin_lecture_type")],
            [InlineKeyboardButton("📝 Notes (PDF)", callback_data="admin_type_notes")],
            [InlineKeyboardButton("📊 DPP (PDF)", callback_data="admin_type_dpp")],
            get_back_button("admin_main"),
            [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
        ]
        
        subject = admin_state.get("subject", "Unknown")
        update.message.reply_text(
            f"📝 *Adding to:*\n"
            f"📘 *Subject:* {subject.capitalize()}\n"
            f"📖 *Chapter:* {chapter_name}\n\n"
            f"Select content type to upload:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif admin_state.get("step") == "ask_lecture_no":
        lecture_no = update.message.text.strip()
        if not lecture_no:
            update.message.reply_text("❌ Please enter a valid lecture number.")
            return
        
        # Validate lecture number
        try:
            if not re.match(r'^[0-9]+(\.[0-9]+)?[A-Za-z]?$', lecture_no):
                update.message.reply_text("❌ Please enter a valid lecture number (e.g., 1, 2.1, 3A).")
                return
        except:
            update.message.reply_text("❌ Please enter a valid lecture number.")
            return
        
        admin_state["lecture_no"] = lecture_no
        admin_state["step"] = "upload"
        admin_state["ctype"] = "lecture"
        
        subject = admin_state.get("subject", "Unknown")
        chapter = admin_state.get("chapter", "Unknown")
        
        keyboard = [
            get_back_button("admin_main"),
            [InlineKeyboardButton("❌ Cancel & Exit", callback_data="exit_admin_mode")]
        ]
        
        update.message.reply_text(
            f"⬆️ *Uploading Lecture {lecture_no} to:*\n"
            f"📘 *Subject:* {subject.capitalize()}\n"
            f"📖 *Chapter:* {chapter}\n\n"
            f"Please send the video file now:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    elif admin_state.get("step") == "upload":
        subject = admin_state.get("subject")
        chapter = admin_state.get("chapter")
        ctype = admin_state.get("ctype")
        lecture_no = admin_state.get("lecture_no")
        
        if not all([subject, chapter, ctype]):
            update.message.reply_text(
                "❌ *Error: Missing data.*\nPlease start over with /vishal",
                parse_mode="Markdown"
            )
            admin_state.clear()
            return
        
        # Get file ID and file name
        file_id = None
        file_name = None
        
        if ctype == "lecture" and update.message.video:
            file_id = update.message.video.file_id
            if update.message.video.file_name:
                file_name = update.message.video.file_name
            else:
                file_name = f"{chapter}_lecture_{lecture_no}.mp4"
        elif ctype in ["notes", "dpp"] and update.message.document:
            file_id = update.message.document.file_id
            if update.message.document.file_name:
                file_name = update.message.document.file_name
            else:
                file_name = f"{chapter}_{ctype}.pdf"
        
        if not file_id:
            update.message.reply_text(
                f"❌ *Invalid File Type*\n\nFor *lectures*: Send MP4 video\nFor *notes/DPP*: Send PDF document",
                parse_mode="Markdown"
            )
            return
        
        # Save to database
        db = load_db()
        db.setdefault(subject, {})
        db[subject].setdefault(chapter, {})
        
        if ctype == "lecture":
            # Initialize lecture as dictionary if not exists
            if "lecture" not in db[subject][chapter] or not isinstance(db[subject][chapter]["lecture"], dict):
                db[subject][chapter]["lecture"] = {}
            
            # Store lecture with number
            db[subject][chapter]["lecture"][lecture_no] = file_id
        else:
            # For notes and DPP, store directly
            db[subject][chapter][ctype] = file_id
        
        save_db(db)
        
        print(f"✅ SAVED: Subject='{subject}', Chapter='{chapter}', Type='{ctype}', LectureNo='{lecture_no}'")
        
        # Success message to admin
        content_type_names = {
            "lecture": "Lecture Video",
            "notes": "Notes",
            "dpp": "DPP"
        }
        
        success_text = (
            f"✅ *{content_type_names.get(ctype, ctype)} Saved Successfully!*\n\n"
            f"📘 *Subject:* {subject.capitalize()}\n"
            f"📖 *Chapter:* {chapter}\n"
        )
        
        if ctype == "lecture":
            success_text += f"🔢 *Lecture No:* {lecture_no}\n"
        
        success_text += (
            f"📁 *Type:* {content_type_names.get(ctype, ctype)}\n"
            f"📄 *File:* {file_name}\n"
            f"📍 *Path:* `/{subject}/{chapter}/{ctype}"
        )
        
        if ctype == "lecture":
            success_text += f"/{lecture_no}`"
        else:
            success_text += "`"
        
        success_text += f"\n\n✅ *Content is now visible to all users!*\n"
        success_text += f"📢 *Notification sent to {len(user_notifications)} users!*"
        
        update.message.reply_text(
            success_text,
            parse_mode="Markdown"
        )
        
        # Send notification to ALL users
        broadcast_new_content(context, subject, chapter, ctype, file_name, lecture_no)
        
        # Show next options
        keyboard = []
        
        if ctype == "lecture":
            keyboard.append([InlineKeyboardButton(f"📤 Add another lecture to '{chapter}'", 
                                                callback_data=f"admin_edit_{subject}_{clean_chapter_name(chapter)}")])
        else:
            keyboard.append([InlineKeyboardButton(f"📤 Add more to '{chapter}'", 
                                                callback_data=f"admin_edit_{subject}_{clean_chapter_name(chapter)}")])
        
        keyboard.append([InlineKeyboardButton(f"📁 Select another chapter in {subject.capitalize()}", 
                                            callback_data=f"admin_existing_{subject}")])
        keyboard.append(get_back_button("admin_main"))
        keyboard.append([InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")])
        
        update.message.reply_text(
            "📋 *What would you like to do next?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Keep subject and chapter in state for easy adding more
        admin_state.clear()
        admin_state["subject"] = subject
        admin_state["chapter"] = chapter
        admin_state["step"] = "type"
        return

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("vishal", admin))
    dp.add_handler(CommandHandler("out", out))
    
    dp.add_handler(CallbackQueryHandler(admin_type, pattern="^admin_type_"))
    dp.add_handler(CallbackQueryHandler(callback_handler))
    
    dp.add_handler(MessageHandler(Filters.all, message_handler))
    
    print("🤖 Board Booster Bot is running...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("✅ Uploaded content is visible to ALL users")
    print("🔔 Users will get notifications for new content")
    print("🗑️ Admin can delete chapters and content")
    print("📹 Multiple lectures per chapter with lecture numbers")
    print("📁 Admin can select existing chapters to add more content")
    print("🔧 Commands: /start, /vishal (admin), /out (exit admin)")
    print("🌐 Website: www.setugyan.live")
    print("🐛 Debug mode: ON")
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
