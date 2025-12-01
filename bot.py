import json
import re
import os
import base64
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

def check_database():
    """Check if database exists and is valid"""
    if not os.path.exists(DB_FILE):
        print(f"⚠️ Database file '{DB_FILE}' does not exist. Creating empty database.")
        with open(DB_FILE, "w") as f:
            json.dump({}, f)
        return False
    
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
        print(f"✅ Database loaded: {len(data)} subjects")
        return True
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def load_db():
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            print(f"📂 DEBUG: Database loaded successfully: {len(data)} subjects")
            return data
    except FileNotFoundError:
        print(f"📂 DEBUG: Database file not found, creating empty database")
        return {}
    except json.JSONDecodeError as e:
        print(f"❌ DEBUG: JSON decode error: {e}")
        return {}
    except Exception as e:
        print(f"❌ DEBUG: Error loading database: {e}")
        return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"💾 DEBUG: Database saved: {len(data)} subjects")

def clean_chapter_name(chapter):
    """Clean chapter name for callback data"""
    if not chapter:
        return ""
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', chapter)
    cleaned = cleaned.lower().strip().replace(' ', '_')
    return cleaned

def encode_chapter_name(chapter_name):
    """Encode chapter name for callback data using base64."""
    try:
        encoded = base64.urlsafe_b64encode(chapter_name.encode('utf-8')).decode('utf-8')
        # Remove padding to make it shorter
        return encoded.rstrip('=')
    except:
        # Fallback to cleaned name if encoding fails
        return clean_chapter_name(chapter_name)

def decode_chapter_name(encoded_name):
    """Decode chapter name from callback data."""
    try:
        # Add padding back if needed
        padding = 4 - (len(encoded_name) % 4)
        if padding != 4:
            encoded_name += '=' * padding
        decoded = base64.urlsafe_b64decode(encoded_name.encode('utf-8')).decode('utf-8')
        return decoded
    except:
        # If decoding fails, return as-is
        return encoded_name

def find_original_chapter(subject, chapter_encoded):
    """Find original chapter name from encoded callback name"""
    db = load_db()
    if subject not in db:
        return None
    
    # First try to decode as base64
    try:
        decoded_name = decode_chapter_name(chapter_encoded)
        print(f"🔍 DEBUG find_original_chapter: decoded='{decoded_name}'")
        
        # Check if decoded name exists exactly
        if decoded_name in db[subject]:
            return decoded_name
    except:
        pass
    
    # If not found, try with cleaned name matching
    for stored_chapter in db[subject].keys():
        # Try exact match with encoded version
        if encode_chapter_name(stored_chapter) == chapter_encoded:
            return stored_chapter
        
        # Try cleaned name match
        if clean_chapter_name(stored_chapter) == chapter_encoded:
            return stored_chapter
        
        # Try case-insensitive match
        if stored_chapter.lower().replace(' ', '_') == chapter_encoded.lower():
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
        [InlineKeyboardButton("📚 Quick Add to Chapter", callback_data="admin_quick_add")],
        [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
    ]
    
    update.message.reply_text(
        "⚙️ *Admin Panel*\n\nWhat would you like to do?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# NEW COMMAND: /chapter - Show all chapters
def chapter_command(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return update.message.reply_text("❌ Access Denied. Admin only.")
    
    db = load_db()
    
    if not db:
        update.message.reply_text(
            "📭 *No chapters found*\n\n"
            "No subjects or chapters have been added yet.\n\n"
            "Use `/chapter <subject> <chapter_name>` to add a new chapter,\n"
            "or use the admin panel with `/vishal`",
            parse_mode="Markdown"
        )
        return
    
    # Check if arguments were provided
    if context.args:
        args = context.args
        
        if len(args) == 1:
            # Only chapter name provided, ask for subject
            chapter_name = args[0]
            return ask_for_subject(update, chapter_name)
        elif len(args) >= 2:
            # Both subject and chapter name provided
            subject = args[0].lower()
            chapter_name = " ".join(args[1:])
            
            # Validate subject
            valid_subjects = ["physics", "chemistry", "maths", "english"]
            if subject not in valid_subjects:
                update.message.reply_text(
                    f"❌ *Invalid Subject*\n\n"
                    f"Available subjects: Physics, Chemistry, Maths, English\n\n"
                    f"Usage: `/chapter <subject> <chapter_name>`\n"
                    f"Example: `/chapter physics Motion in a Straight Line`",
                    parse_mode="Markdown"
                )
                return
            
            return show_chapter_details(update, context, subject, chapter_name)
    
    # No arguments: show all chapters grouped by subject
    message = "📚 *All Chapters*\n\n"
    
    for subject in sorted(db.keys()):
        message += f"📘 *{subject.capitalize()}*\n"
        chapters = list(db[subject].keys())
        chapters.sort()
        
        for i, ch in enumerate(chapters, 1):
            # Count content
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
            
            message += f"  {i}. {ch} ({content_count} items)\n"
        
        message += "\n"
    
    message += "\n*Commands:*\n"
    message += "• `/chapter <chapter_name>` - Add/View chapter (will ask for subject)\n"
    message += "• `/chapter <subject> <chapter_name>` - Directly add/view chapter\n"
    message += "• `/vishal` - Open admin panel\n"
    message += "• `/out` - Exit admin mode"
    
    keyboard = [
        [InlineKeyboardButton("📁 Open Admin Panel", callback_data="back_to_admin_main")],
        [InlineKeyboardButton("➕ Add New Chapter", callback_data="admin_new_chapter")]
    ]
    
    update.message.reply_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def ask_for_subject(update: Update, chapter_name):
    """Ask admin to select a subject for the new chapter"""
    keyboard = [
        [InlineKeyboardButton("📘 Physics", callback_data=f"new_chapter_subject_physics_{chapter_name}")],
        [InlineKeyboardButton("🧪 Chemistry", callback_data=f"new_chapter_subject_chemistry_{chapter_name}")],
        [InlineKeyboardButton("📐 Maths", callback_data=f"new_chapter_subject_maths_{chapter_name}")],
        [InlineKeyboardButton("📖 English", callback_data=f"new_chapter_subject_english_{chapter_name}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="back_to_admin_main")]
    ]
    
    update.message.reply_text(
        f"📝 *Select Subject for New Chapter*\n\n"
        f"Chapter Name: *{chapter_name}*\n\n"
        f"Please select a subject:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def show_chapter_details(update: Update, context: CallbackContext, subject, chapter_name):
    """Show details of a specific chapter and options to add content"""
    db = load_db()
    
    # Check if chapter exists in the specified subject
    chapter_exists = False
    exact_chapter_name = None
    
    if subject in db:
        # Check for exact match first
        if chapter_name in db[subject]:
            chapter_exists = True
            exact_chapter_name = chapter_name
        else:
            # Check for case-insensitive match
            for ch in db[subject].keys():
                if ch.lower() == chapter_name.lower():
                    chapter_exists = True
                    exact_chapter_name = ch
                    break
    
    if not chapter_exists:
        # Chapter doesn't exist, ask for confirmation to create it
        encoded_chapter = encode_chapter_name(chapter_name)
        keyboard = [
            [InlineKeyboardButton(f"✅ Yes, Create in {subject.capitalize()}", 
                                 callback_data=f"confirm_create_chapter_{subject}_{encoded_chapter}")],
            [InlineKeyboardButton("🔄 Change Subject", 
                                 callback_data=f"ask_subject_for_{encoded_chapter}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="back_to_admin_main")]
        ]
        
        update.message.reply_text(
            f"📝 *Create New Chapter*\n\n"
            f"📘 *Subject:* {subject.capitalize()}\n"
            f"📖 *Chapter:* {chapter_name}\n\n"
            f"Chapter doesn't exist yet. Create it in {subject.capitalize()}?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # Chapter exists, show details and options
    chapter_data = db[subject][exact_chapter_name]
    
    # Build content summary
    content_summary = []
    if "lecture" in chapter_data:
        if isinstance(chapter_data["lecture"], dict):
            lect_count = len(chapter_data["lecture"])
            content_summary.append(f"🎥 {lect_count} lecture(s)")
        else:
            content_summary.append("🎥 1 lecture")
    if "notes" in chapter_data:
        content_summary.append("📝 Notes")
    if "dpp" in chapter_data:
        content_summary.append("📊 DPP")
    
    content_text = " | ".join(content_summary) if content_summary else "No content yet"
    
    # Prepare message
    message = (
        f"📚 *Chapter Details*\n\n"
        f"📘 *Subject:* {subject.capitalize()}\n"
        f"📖 *Chapter:* {exact_chapter_name}\n"
        f"📦 *Content:* {content_text}\n\n"
        f"*Options:*"
    )
    
    # Prepare keyboard
    keyboard = []
    
    encoded_chapter = encode_chapter_name(exact_chapter_name)
    
    # Add content buttons
    keyboard.append([InlineKeyboardButton("🎥 Add Lecture", callback_data=f"quick_add_lecture_{subject}_{encoded_chapter}")])
    keyboard.append([InlineKeyboardButton("📝 Add Notes", callback_data=f"quick_add_notes_{subject}_{encoded_chapter}")])
    keyboard.append([InlineKeyboardButton("📊 Add DPP", callback_data=f"quick_add_dpp_{subject}_{encoded_chapter}")])
    
    # View existing content
    if content_summary:
        keyboard.append([InlineKeyboardButton("👁️ View Content", callback_data=f"view_chapter_content_{subject}_{encoded_chapter}")])
    
    # Delete option
    keyboard.append([InlineKeyboardButton("🗑️ Delete Chapter", callback_data=f"delete_chapter_quick_{subject}_{encoded_chapter}")])
    
    # Navigation
    keyboard.append([InlineKeyboardButton("🔙 Back to All Chapters", callback_data="back_to_chapters_list")])
    keyboard.append([InlineKeyboardButton("📋 Admin Panel", callback_data="back_to_admin_main")])
    
    update.message.reply_text(
        message,
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
    elif back_to == "chapters_list":
        return [InlineKeyboardButton("🔙 Back to Chapters List", callback_data="back_to_chapters_list")]

# Global admin state
admin_state = {}

def show_chapter_callback(query, subject, chapter_name):
    """Show chapter details in callback query"""
    db = load_db()
    
    # Make sure chapter exists
    if subject not in db or chapter_name not in db[subject]:
        # Create it if it doesn't exist
        if subject not in db:
            db[subject] = {}
        db[subject][chapter_name] = {}
        save_db(db)
    
    chapter_data = db[subject][chapter_name]
    
    # Build content summary
    content_summary = []
    if "lecture" in chapter_data:
        if isinstance(chapter_data["lecture"], dict):
            lect_count = len(chapter_data["lecture"])
            content_summary.append(f"🎥 {lect_count} lecture(s)")
        else:
            content_summary.append("🎥 1 lecture")
    if "notes" in chapter_data:
        content_summary.append("📝 Notes")
    if "dpp" in chapter_data:
        content_summary.append("📊 DPP")
    
    content_text = " | ".join(content_summary) if content_summary else "No content yet"
    
    encoded_chapter = encode_chapter_name(chapter_name)
    
    message = (
        f"📚 *Chapter Details*\n\n"
        f"📘 *Subject:* {subject.capitalize()}\n"
        f"📖 *Chapter:* {chapter_name}\n"
        f"📦 *Content:* {content_text}\n\n"
        f"*Options:*"
    )
    
    keyboard = []
    keyboard.append([InlineKeyboardButton("🎥 Add Lecture", callback_data=f"quick_add_lecture_{subject}_{encoded_chapter}")])
    keyboard.append([InlineKeyboardButton("📝 Add Notes", callback_data=f"quick_add_notes_{subject}_{encoded_chapter}")])
    keyboard.append([InlineKeyboardButton("📊 Add DPP", callback_data=f"quick_add_dpp_{subject}_{encoded_chapter}")])
    
    if content_summary:
        keyboard.append([InlineKeyboardButton("👁️ View Content", callback_data=f"view_chapter_content_{subject}_{encoded_chapter}")])
    
    keyboard.append([InlineKeyboardButton("🗑️ Delete Chapter", callback_data=f"delete_chapter_quick_{subject}_{encoded_chapter}")])
    keyboard.append([InlineKeyboardButton("🔙 Back to All Chapters", callback_data="back_to_chapters_list")])
    keyboard.append([InlineKeyboardButton("📋 Admin Panel", callback_data="back_to_admin_main")])
    
    query.edit_message_text(
        message,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

    print(f"🔍 DEBUG: Callback data received: {data}")

    # ============== NEW: Subject Selection for Chapter Creation ==============
    elif data.startswith("new_chapter_subject_"):
        # Format: new_chapter_subject_physics_ChapterName
        parts = data.split("_", 4)
        if len(parts) >= 5:
            subject = parts[3]
            chapter_name = parts[4]
            
            # Show chapter details
            show_chapter_callback(query, subject, chapter_name)
        return
    
    elif data.startswith("ask_subject_for_"):
        # User wants to change subject for chapter creation
        encoded_chapter = data.replace("ask_subject_for_", "")
        chapter_name = decode_chapter_name(encoded_chapter)
        
        keyboard = [
            [InlineKeyboardButton("📘 Physics", callback_data=f"new_chapter_subject_physics_{chapter_name}")],
            [InlineKeyboardButton("🧪 Chemistry", callback_data=f"new_chapter_subject_chemistry_{chapter_name}")],
            [InlineKeyboardButton("📐 Maths", callback_data=f"new_chapter_subject_maths_{chapter_name}")],
            [InlineKeyboardButton("📖 English", callback_data=f"new_chapter_subject_english_{chapter_name}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="back_to_admin_main")]
        ]
        
        query.edit_message_text(
            f"📝 *Select Subject for New Chapter*\n\n"
            f"Chapter Name: *{chapter_name}*\n\n"
            f"Please select a subject:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data.startswith("confirm_create_chapter_"):
        # Format: confirm_create_chapter_subject_encodedChapterName
        parts = data.split("_", 3)
        if len(parts) >= 4:
            subject = parts[2]
            encoded_chapter = parts[3]
            
            chapter_name = decode_chapter_name(encoded_chapter)
            
            # Create the chapter in database
            db = load_db()
            if subject not in db:
                db[subject] = {}
            
            if chapter_name not in db[subject]:
                db[subject][chapter_name] = {}
                save_db(db)
                
                query.answer(f"✅ Chapter '{chapter_name}' created in {subject}", show_alert=True)
            
            # Now show the chapter details
            show_chapter_callback(query, subject, chapter_name)
        return

    # ============== NEW: Quick Chapter Management ==============
    elif data == "back_to_chapters_list":
        # Simulate /chapter command
        db = load_db()
        
        if not db:
            query.edit_message_text(
                "📭 *No chapters found*\n\n"
                "No subjects or chapters have been added yet.",
                parse_mode="Markdown"
            )
            return
        
        message = "📚 *All Chapters*\n\n"
        
        for subject in sorted(db.keys()):
            message += f"📘 *{subject.capitalize()}*\n"
            chapters = list(db[subject].keys())
            chapters.sort()
            
            for i, ch in enumerate(chapters, 1):
                # Count content
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
                
                message += f"  {i}. {ch} ({content_count} items)\n"
            
            message += "\n"
        
        keyboard = [
            [InlineKeyboardButton("📁 Open Admin Panel", callback_data="back_to_admin_main")],
            [InlineKeyboardButton("➕ Add New Chapter", callback_data="admin_new_chapter")]
        ]
        
        query.edit_message_text(
            message,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data.startswith("quick_add_lecture_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            subject = parts[2]
            encoded_chapter = parts[3]
            
            chapter_name = decode_chapter_name(encoded_chapter)
            
            admin_state["subject"] = subject
            admin_state["chapter"] = chapter_name
            admin_state["step"] = "lecture_no"
            
            # Check existing lectures
            db = load_db()
            existing_lectures = []
            if subject in db and chapter_name in db[subject] and "lecture" in db[subject][chapter_name]:
                if isinstance(db[subject][chapter_name]["lecture"], dict):
                    existing_lectures = list(db[subject][chapter_name]["lecture"].keys())
                    existing_lectures.sort(key=lambda x: int(x) if x.isdigit() else x)
            
            keyboard = []
            if existing_lectures:
                keyboard.append([InlineKeyboardButton("➕ Add New Lecture Number", callback_data="admin_new_lecture_no")])
                
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
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Chapter", callback_data=f"back_to_chapter_{subject}_{encoded_chapter}")])
            
            status_text = ""
            if existing_lectures:
                status_text = f"\n\n📹 *Existing lectures:* {', '.join(existing_lectures)}"
            
            query.edit_message_text(
                f"📝 *Adding Lecture to:*\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {chapter_name}\n\n"
                f"Select lecture number or add new:{status_text}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif data.startswith("quick_add_notes_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            subject = parts[2]
            encoded_chapter = parts[3]
            
            chapter_name = decode_chapter_name(encoded_chapter)
            
            admin_state["subject"] = subject
            admin_state["chapter"] = chapter_name
            admin_state["ctype"] = "notes"
            admin_state["step"] = "upload"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Chapter", callback_data=f"back_to_chapter_{subject}_{encoded_chapter}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="back_to_admin_main")]
            ]
            
            query.edit_message_text(
                f"⬆️ *Uploading Notes to:*\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {chapter_name}\n\n"
                f"*Upload Notes PDF:*\n\nPlease send the PDF file now:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif data.startswith("quick_add_dpp_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            subject = parts[2]
            encoded_chapter = parts[3]
            
            chapter_name = decode_chapter_name(encoded_chapter)
            
            admin_state["subject"] = subject
            admin_state["chapter"] = chapter_name
            admin_state["ctype"] = "dpp"
            admin_state["step"] = "upload"
            
            keyboard = [
                [InlineKeyboardButton("🔙 Back to Chapter", callback_data=f"back_to_chapter_{subject}_{encoded_chapter}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="back_to_admin_main")]
            ]
            
            query.edit_message_text(
                f"⬆️ *Uploading DPP to:*\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {chapter_name}\n\n"
                f"*Upload DPP PDF:*\n\nPlease send the PDF file now:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif data.startswith("view_chapter_content_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            subject = parts[2]
            encoded_chapter = parts[3]
            
            chapter_name = decode_chapter_name(encoded_chapter)
            
            # Show chapter content
            db = load_db()
            if subject in db and chapter_name in db[subject]:
                chapter_data = db[subject][chapter_name]
                
                message = f"📚 *{chapter_name}* - Content\n\n"
                
                # Lectures
                if "lecture" in chapter_data:
                    if isinstance(chapter_data["lecture"], dict):
                        lecture_numbers = list(chapter_data["lecture"].keys())
                        lecture_numbers.sort(key=lambda x: int(x) if x.isdigit() else x)
                        message += f"🎥 *Lectures:* {len(lecture_numbers)} lectures\n"
                        message += f"   Numbers: {', '.join(lecture_numbers)}\n\n"
                    else:
                        message += "🎥 *Lectures:* 1 lecture\n\n"
                
                # Notes
                if "notes" in chapter_data:
                    message += "📝 *Notes:* Available ✅\n\n"
                else:
                    message += "📝 *Notes:* Not available ❌\n\n"
                
                # DPP
                if "dpp" in chapter_data:
                    message += "📊 *DPP:* Available ✅\n\n"
                else:
                    message += "📊 *DPP:* Not available ❌\n\n"
                
                keyboard = [
                    [InlineKeyboardButton("🎥 Add Lecture", callback_data=f"quick_add_lecture_{subject}_{encoded_chapter}")],
                    [InlineKeyboardButton("📝 Add Notes", callback_data=f"quick_add_notes_{subject}_{encoded_chapter}")],
                    [InlineKeyboardButton("📊 Add DPP", callback_data=f"quick_add_dpp_{subject}_{encoded_chapter}")],
                    [InlineKeyboardButton("🔙 Back to Chapter", callback_data=f"back_to_chapter_{subject}_{encoded_chapter}")]
                ]
                
                query.edit_message_text(
                    message,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        return
    
    elif data.startswith("back_to_chapter_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            subject = parts[2]
            encoded_chapter = parts[3]
            
            chapter_name = decode_chapter_name(encoded_chapter)
            show_chapter_callback(query, subject, chapter_name)
        return
    
    elif data.startswith("delete_chapter_quick_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            subject = parts[2]
            encoded_chapter = parts[3]
            
            chapter_name = decode_chapter_name(encoded_chapter)
            
            keyboard = [
                [InlineKeyboardButton("✅ YES, Delete Chapter", callback_data=f"execute_delete_quick_{subject}_{encoded_chapter}")],
                [InlineKeyboardButton("❌ NO, Cancel", callback_data=f"back_to_chapter_{subject}_{encoded_chapter}")]
            ]
            
            query.edit_message_text(
                f"⚠️ *CONFIRM DELETION*\n\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {chapter_name}\n\n"
                f"❌ *This will delete ALL content in this chapter!*\n\n"
                f"Are you sure you want to delete this chapter?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
    
    elif data.startswith("execute_delete_quick_"):
        parts = data.split("_", 3)
        if len(parts) >= 4:
            subject = parts[2]
            encoded_chapter = parts[3]
            
            chapter_name = decode_chapter_name(encoded_chapter)
            
            # Delete chapter
            db = load_db()
            if subject in db and chapter_name in db[subject]:
                del db[subject][chapter_name]
                
                # Remove subject if empty
                if not db[subject]:
                    del db[subject]
                
                save_db(db)
                
                query.edit_message_text(
                    f"✅ *Chapter Deleted Successfully!*\n\n"
                    f"📘 *Subject:* {subject.capitalize()}\n"
                    f"📖 *Chapter:* {chapter_name}\n\n"
                    f"The chapter has been removed.",
                    parse_mode="Markdown"
                )
            else:
                query.edit_message_text("❌ Chapter not found.")
        
        # Return to chapters list
        query.message.reply_text(
            "📚 *Chapters List*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 View All Chapters", callback_data="back_to_chapters_list")]])
        )
        return
    
    # ============== BACK BUTTON HANDLERS ==============
    elif data == "back_subjects":
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
            [InlineKeyboardButton("📚 Quick Add to Chapter", callback_data="admin_quick_add")],
            [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
        ]
        query.edit_message_text(
            "⚙️ *Admin Panel*\n\nWhat would you like to do?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "admin_quick_add":
        # Show all chapters for quick access
        db = load_db()
        
        if not db:
            query.edit_message_text(
                "📭 *No chapters found*\n\n"
                "No subjects or chapters have been added yet.",
                parse_mode="Markdown"
            )
            return
        
        keyboard = []
        for subject in sorted(db.keys()):
            chapters = list(db[subject].keys())
            chapters.sort()
            
            for ch in chapters:
                encoded_chapter = encode_chapter_name(ch)
                keyboard.append([
                    InlineKeyboardButton(
                        f"📘 {subject.capitalize()}: {ch}", 
                        callback_data=f"back_to_chapter_{subject}_{encoded_chapter}"
                    )
                ])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_main")])
        
        query.edit_message_text(
            "📚 *Quick Add to Chapter*\n\nSelect a chapter to add content:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    # ============== Handle selecting a specific chapter to edit ==============
    elif data.startswith("admin_edit_"):
        print(f"🔍 DEBUG admin_edit_: Received data: {data}")
        
        # Parse the callback data
        try:
            parts = data.split("_", 2)
            if len(parts) != 3:
                query.answer("❌ Invalid format", show_alert=True)
                return
            
            subject = parts[1]
            encoded_chapter = parts[2]
            
            chapter_name = decode_chapter_name(encoded_chapter)
            
            print(f"🔍 DEBUG: Subject={subject}, Chapter={chapter_name}")
            
            # Load database
            db = load_db()
            
            # Check if subject exists
            if subject not in db:
                query.answer(f"❌ Subject '{subject}' not found", show_alert=True)
                return
            
            # Find the chapter
            found_chapter = None
            if chapter_name in db[subject]:
                found_chapter = chapter_name
            else:
                # Try case-insensitive match
                for db_chapter in db[subject].keys():
                    if db_chapter.lower() == chapter_name.lower():
                        found_chapter = db_chapter
                        break
            
            if not found_chapter:
                query.answer(f"❌ Chapter '{chapter_name}' not found", show_alert=True)
                return
            
            print(f"🔍 DEBUG: Found chapter: {found_chapter}")
            
            # Store in admin state
            admin_state["subject"] = subject
            admin_state["chapter"] = found_chapter
            admin_state["step"] = "type"
            
            # Show content type selection
            keyboard = [
                [InlineKeyboardButton("🎥 Lecture (MP4)", callback_data="admin_lecture_type")],
                [InlineKeyboardButton("📝 Notes (PDF)", callback_data="admin_type_notes")],
                [InlineKeyboardButton("📊 DPP (PDF)", callback_data="admin_type_dpp")],
                [InlineKeyboardButton("🔙 Back", callback_data=f"admin_existing_{subject}")]
            ]
            
            # Check existing content
            existing_content = []
            if subject in db and found_chapter in db[subject]:
                if "lecture" in db[subject][found_chapter]:
                    if isinstance(db[subject][found_chapter]["lecture"], dict):
                        lect_count = len(db[subject][found_chapter]["lecture"])
                        existing_content.append(f"🎥 {lect_count} Lectures")
                    else:
                        existing_content.append("🎥 Lecture")
                if "notes" in db[subject][found_chapter]:
                    existing_content.append("📝 Notes")
                if "dpp" in db[subject][found_chapter]:
                    existing_content.append("📊 DPP")
            
            status_text = ""
            if existing_content:
                status_text = f"\n\n✅ *Already uploaded:* {', '.join(existing_content)}"
            
            query.edit_message_text(
                f"📝 *Adding content to:*\n"
                f"📘 *Subject:* {subject.capitalize()}\n"
                f"📖 *Chapter:* {found_chapter}\n\n"
                f"Select content type to upload:{status_text}",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            print(f"❌ ERROR in admin_edit_: {str(e)}")
            query.answer("❌ Error loading chapter", show_alert=True)
        return
    
    # ============== Handle admin content type selection ==============
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
    
    elif data == "admin_type_notes":
        admin_state["ctype"] = "notes"
        admin_state["step"] = "upload"
        
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
            f"*Upload Notes PDF:*\n\nPlease send the PDF file now:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    
    elif data == "admin_type_dpp":
        admin_state["ctype"] = "dpp"
        admin_state["step"] = "upload"
        
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
            f"*Upload DPP PDF:*\n\nPlease send the PDF file now:",
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
    elif data == "exit_admin_mode":
        admin_state.clear()
        query.edit_message_text(
            "✅ *Exited Admin Mode*\n\nUse /start to browse content.",
            parse_mode="Markdown"
        )
        return

    # ============== (Rest of your existing callback handlers) ==============
    # ... [Your existing callback handlers for user access, delete mode, etc.]

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
        encoded_chapter = encode_chapter_name(chapter)
        keyboard = []
        
        keyboard.append([InlineKeyboardButton(f"📤 Add more to '{chapter}'", 
                                            callback_data=f"back_to_chapter_{subject}_{encoded_chapter}")])
        
        keyboard.append([InlineKeyboardButton(f"📁 Select another chapter in {subject.capitalize()}", 
                                            callback_data=f"admin_existing_{subject}")])
        keyboard.append(get_back_button("admin_main"))
        keyboard.append([InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")])
        
        update.message.reply_text(
            "📋 *What would you like to do next?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Clear admin state
        admin_state.clear()
        return

def main():
    # Check and initialize database
    if not check_database():
        print("⚠️ Database issues detected. Bot may not show content until admin uploads files.")
    
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("vishal", admin))
    dp.add_handler(CommandHandler("out", out))
    dp.add_handler(CommandHandler("chapter", chapter_command))  # NEW COMMAND
    
    # Only one callback handler needed
    dp.add_handler(CallbackQueryHandler(callback_handler))
    
    dp.add_handler(MessageHandler(Filters.all, message_handler))
    
    print("🤖 Board Booster Bot is running...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print("✅ Uploaded content is visible to ALL users")
    print("🔔 Users will get notifications for new content")
    print("📚 NEW: /chapter command for quick chapter management")
    print("   • `/chapter` - Show all chapters")
    print("   • `/chapter <chapter_name>` - Ask for subject, then create/view")
    print("   • `/chapter <subject> <chapter_name>` - Direct create/view")
    print("🗑️ Admin can delete chapters and content")
    print("📹 Multiple lectures per chapter with lecture numbers")
    print("📁 Admin can select existing chapters to add more content")
    print("🔧 Commands: /start, /vishal (admin), /chapter, /out (exit admin)")
    print("🌐 Website: www.setugyan.live")
    print("🐛 Debug mode: ON")
    print("💾 Database check: COMPLETE")
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
