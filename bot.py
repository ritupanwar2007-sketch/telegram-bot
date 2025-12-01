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
        [InlineKeyboardButton("📁 Select Existing Chapter", callback_data="admin_select_chapter")],
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

def broadcast_new_content(context: CallbackContext, subject, chapter, content_type, file_name=None):
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
        f"📁 *Type:* {content_type_names.get(content_type, content_type)}\n"
        f"📍 *Path:* `/{subject}/{chapter}/{content_type}`\n\n"
        f"👉 Use /start to access it now!"
    )
    
    if file_name:
        notification_text += f"\n📄 *File:* {file_name}"
    
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

def subject_keyboard(mode, include_back=False):
    keyboard = [
        [InlineKeyboardButton("📘 Physics", callback_data=f"{mode}_sub_physics")],
        [InlineKeyboardButton("🧪 Chemistry", callback_data=f"{mode}_sub_chemistry")],
        [InlineKeyboardButton("📐 Maths", callback_data=f"{mode}_sub_maths")],
        [InlineKeyboardButton("📖 English", callback_data=f"{mode}_sub_english")]
    ]
    
    if include_back:
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_admin_main")])
    
    return InlineKeyboardMarkup(keyboard)

def get_back_button(back_to, data=None):
    if back_to == "subjects":
        return [InlineKeyboardButton("🔙 Back to Subjects", callback_data="back_subjects")]
    elif back_to == "chapters":
        return [InlineKeyboardButton("🔙 Back to Chapters", callback_data=f"back_chapters_{data}")]
    elif back_to == "types":
        return [InlineKeyboardButton("🔙 Back to Content Types", callback_data=f"back_types_{data}")]
    elif back_to == "admin_subjects":
        return [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="back_admin_subjects")]
    elif back_to == "admin_main":
        return [InlineKeyboardButton("🔙 Back to Admin Main", callback_data="back_to_admin_main")]

# Global admin state
admin_state = {}

def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

    print(f"🔍 DEBUG: Callback data received: {data}")

    # Handle back buttons
    if data == "back_subjects":
        query.edit_message_text(
            "📚 *Choose Subject:*",
            parse_mode="Markdown",
            reply_markup=subject_keyboard("user")
        )
        return
    
    elif data == "back_to_admin_main":
        keyboard = [
            [InlineKeyboardButton("📁 Select Existing Chapter", callback_data="admin_select_chapter")],
            [InlineKeyboardButton("➕ Add New Chapter", callback_data="admin_new_chapter")],
            [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
        ]
        query.edit_message_text(
            "⚙️ *Admin Panel*\n\nWhat would you like to do?",
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
                [InlineKeyboardButton("🎥 Lectures", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_lecture")],
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
        
    elif data == "back_admin_subjects":
        query.edit_message_text(
            "⚙️ *Admin Panel*\nSelect subject to manage:\n\nUse /out to exit admin mode",
            parse_mode="Markdown",
            reply_markup=subject_keyboard("admin")
        )
        return
    
    # Admin main menu options
    elif data == "admin_select_chapter":
        # Show subjects for selecting existing chapter
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
        # Show subjects for adding NEW chapter
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
            f"🎥 = Lecture  📝 = Notes  📊 = DPP  📭 = No content\n\n"
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
            admin_state["step"] = "type"  # Skip chapter name step
            
            # Show content type selection for this chapter
            keyboard = [
                [InlineKeyboardButton("🎥 Lecture (MP4)", callback_data="admin_type_lecture")],
                [InlineKeyboardButton("📝 Notes (PDF)", callback_data="admin_type_notes")],
                [InlineKeyboardButton("📊 DPP (PDF)", callback_data="admin_type_dpp")],
                get_back_button("admin_main")
            ]
            
            # Show what's already uploaded
            db = load_db()
            existing_content = []
            if subject in db and original_chapter in db[subject]:
                if "lecture" in db[subject][original_chapter]:
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

    # Admin subject selection (old way - kept for compatibility)
    if data.startswith("admin_sub_"):
        subject = data.replace("admin_sub_", "")
        admin_state["subject"] = subject
        admin_state["step"] = "chapter"
        
        keyboard = [
            get_back_button("admin_subjects"),
            [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
        ]
        query.edit_message_text(
            f"📘 *{subject.capitalize()} Selected*\n\n📝 Please send the *chapter name*:",
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

    # User subject selection
    if data.startswith("user_sub_"):
        subject = data.replace("user_sub_", "")
        db = load_db()
        if subject not in db or not db[subject]:
            query.edit_message_text(
                f"📭 No content available for *{subject.capitalize()}* yet.\nPlease check back later!",
                parse_mode="Markdown"
            )
            return
        
        chapters = list(db[subject].keys())
        chapters.sort()
        
        keyboard = []
        for ch in chapters:
            callback_name = clean_chapter_name(ch)
            keyboard.append([InlineKeyboardButton(f"📖 {ch}", callback_data=f"user_ch_{subject}_{callback_name}")])
        keyboard.append(get_back_button("subjects"))
        query.edit_message_text(
            f"📂 *{subject.capitalize()} - Select Chapter:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # User chapter selection
    if data.startswith("user_ch_"):
        try:
            parts = data.split("_")
            if len(parts) >= 4:
                subject = parts[2]
                chapter_encoded = "_".join(parts[3:])
            else:
                subject = data.split("_")[2] if len(data.split("_")) > 2 else ""
                chapter_encoded = data.split("_")[3] if len(data.split("_")) > 3 else ""
            
            print(f"🔍 DEBUG: user_ch_ parsed - subject: {subject}, chapter_encoded: {chapter_encoded}")
            
            if not subject or not chapter_encoded:
                query.edit_message_text("❌ Invalid chapter selection.")
                return
            
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                db = load_db()
                print(f"🔍 DEBUG: Database contents for {subject}: {db.get(subject, {})}")
                print(f"🔍 DEBUG: Looking for chapter matching: {chapter_encoded}")
                
                query.edit_message_text(
                    f"❌ Chapter not found.\n\nPlease try selecting the chapter again from the list.",
                    parse_mode="Markdown"
                )
                return
                
            keyboard = [
                [InlineKeyboardButton("🎥 Lectures", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_lecture")],
                [InlineKeyboardButton("📝 Notes", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_notes")],
                [InlineKeyboardButton("📊 DPP", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_dpp")],
            ]
            keyboard.append(get_back_button("chapters", subject))
            query.edit_message_text(
                f"📂 *{original_chapter}*\nSelect content type:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as e:
            print(f"❌ ERROR in user_ch_: {str(e)}")
            query.edit_message_text(
                "❌ Error processing your selection. Please try again.",
                parse_mode="Markdown"
            )
        return

    # User content type selection
    if data.startswith("user_type_"):
        try:
            parts = data.split("_")
            if len(parts) >= 5:
                subject = parts[2]
                chapter_encoded = parts[3]
                ctype = parts[4]
                
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
                        [InlineKeyboardButton("🎥 Lectures", callback_data=f"user_type_{subject}_{clean_chapter_name(original_chapter)}_lecture")],
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
                    if ctype == "lecture":
                        context.bot.send_video(
                            chat_id=query.message.chat_id,
                            video=file_id,
                            caption=f"🎥 *{original_chapter} - Lecture*\n\n_Enjoy your study!_ 📚",
                            parse_mode="Markdown"
                        )
                    else:
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
    
    if data.startswith("admin_type_"):
        ctype = data.replace("admin_type_", "")
        admin_state["ctype"] = ctype
        admin_state["step"] = "upload"
        
        content_type_names = {
            "lecture": "Lecture Video (MP4)",
            "notes": "Notes PDF",
            "dpp": "DPP PDF"
        }
        
        keyboard = [
            get_back_button("admin_main"),
            [InlineKeyboardButton("❌ Cancel & Exit", callback_data="exit_admin_mode")]
        ]
        
        # Show which chapter we're adding to
        subject = admin_state.get("subject", "Unknown")
        chapter = admin_state.get("chapter", "Unknown")
        
        query.edit_message_text(
            f"⬆️ *Uploading to:*\n"
            f"📘 *Subject:* {subject.capitalize()}\n"
            f"📖 *Chapter:* {chapter}\n\n"
            f"*Upload {content_type_names.get(ctype, ctype)}:*\n\nPlease send the file now:",
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
            [InlineKeyboardButton("🎥 Lecture (MP4)", callback_data="admin_type_lecture")],
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

    if admin_state.get("step") == "upload":
        subject = admin_state.get("subject")
        chapter = admin_state.get("chapter")
        ctype = admin_state.get("ctype")
        
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
                file_name = f"{chapter}_lecture.mp4"
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
        db[subject][chapter][ctype] = file_id
        save_db(db)
        
        print(f"✅ SAVED: Subject='{subject}', Chapter='{chapter}', Type='{ctype}'")
        
        # Success message to admin
        content_type_names = {
            "lecture": "Lecture Video",
            "notes": "Notes",
            "dpp": "DPP"
        }
        
        update.message.reply_text(
            f"✅ *{content_type_names.get(ctype, ctype)} Saved Successfully!*\n\n"
            f"📘 *Subject:* {subject.capitalize()}\n"
            f"📖 *Chapter:* {chapter}\n"
            f"📁 *Type:* {content_type_names.get(ctype, ctype)}\n"
            f"📄 *File:* {file_name}\n"
            f"📍 *Path:* `/{subject}/{chapter}/{ctype}`\n\n"
            f"✅ *Content is now visible to all users!*\n"
            f"📢 *Notification sent to {len(user_notifications)} users!*",
            parse_mode="Markdown"
        )
        
        # Send notification to ALL users
        broadcast_new_content(context, subject, chapter, ctype, file_name)
        
        # Show next options - IMPORTANT: Allow adding more to same chapter
        keyboard = [
            [InlineKeyboardButton(f"📤 Add more to '{chapter}'", callback_data=f"admin_edit_{subject}_{clean_chapter_name(chapter)}")],
            [InlineKeyboardButton(f"📁 Select another chapter in {subject.capitalize()}", callback_data=f"admin_existing_{subject}")],
            get_back_button("admin_main"),
            [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
        ]
        update.message.reply_text(
            "📋 *What would you like to do next?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Keep subject in state for easy adding more
        admin_state.clear()
        admin_state["subject"] = subject
        admin_state["step"] = "type"  # Ready to add more content types
        admin_state["chapter"] = chapter  # Keep chapter for adding more
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
    print("📁 Admin can select existing chapters to add more content")
    print("🔧 Commands: /start, /vishal (admin), /out (exit admin)")
    print("🌐 Website: www.setugyan.live")
    print("🐛 Debug mode: ON")
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
