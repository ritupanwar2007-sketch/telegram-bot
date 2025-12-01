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
    """Clean chapter name for callback data (remove special chars, lowercase)"""
    if not chapter:
        return ""
    # Replace spaces with underscores and remove special characters
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', chapter)  # Remove special chars
    cleaned = cleaned.lower().strip().replace(' ', '_')
    return cleaned

def find_original_chapter(subject, chapter_encoded):
    """Find original chapter name from encoded callback name"""
    db = load_db()
    if subject not in db:
        return None
    
    # Try exact match first
    if chapter_encoded in db[subject]:
        return chapter_encoded
    
    # Try cleaned version match
    for stored_chapter in db[subject].keys():
        if clean_chapter_name(stored_chapter) == chapter_encoded:
            return stored_chapter
    
    # Try reverse: if encoded is already cleaned, find original
    for stored_chapter in db[subject].keys():
        if stored_chapter.lower().replace(' ', '_') == chapter_encoded:
            return stored_chapter
    
    return None

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "📚 *Board Booster Bot*\n_Created by Vishal_\n\nChoose your subject:",
        parse_mode="Markdown",
        reply_markup=subject_keyboard("user")
    )

def admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return update.message.reply_text("❌ Access Denied. Admin only.")
    update.message.reply_text(
        "⚙️ *Admin Panel*\nSelect subject to manage:\n\nUse /out to exit admin mode",
        parse_mode="Markdown",
        reply_markup=subject_keyboard("admin")
    )

def out(update: Update, context: CallbackContext):
    """Exit admin panel and clear admin state"""
    if update.message.from_user.id != ADMIN_ID:
        return update.message.reply_text("❌ Access Denied.")
    
    # Clear admin state
    global admin_state
    admin_state.clear()
    
    update.message.reply_text(
        "✅ *Exited Admin Panel*\n\nYou are now in user mode. Use /start to browse content.",
        parse_mode="Markdown"
    )

def subject_keyboard(mode):
    keyboard = [
        [InlineKeyboardButton("📘 Physics", callback_data=f"{mode}_sub_physics")],
        [InlineKeyboardButton("🧪 Chemistry", callback_data=f"{mode}_sub_chemistry")],
        [InlineKeyboardButton("📐 Maths", callback_data=f"{mode}_sub_maths")],
        [InlineKeyboardButton("📖 English", callback_data=f"{mode}_sub_english")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button(back_to, data=None):
    """Create a back button with arrow symbol"""
    if back_to == "subjects":
        return [InlineKeyboardButton("🔙 Back to Subjects", callback_data="back_subjects")]
    elif back_to == "chapters":
        return [InlineKeyboardButton("🔙 Back to Chapters", callback_data=f"back_chapters_{data}")]
    elif back_to == "types":
        return [InlineKeyboardButton("🔙 Back to Content Types", callback_data=f"back_types_{data}")]
    elif back_to == "admin_subjects":
        return [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="back_admin_subjects")]

# Global admin state
admin_state = {}

def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

    print(f"🔍 DEBUG: Callback data received: {data}")  # Debug log

    # Handle back buttons
    if data == "back_subjects":
        query.edit_message_text(
            "📚 *Choose Subject:*",
            parse_mode="Markdown",
            reply_markup=subject_keyboard("user")
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
        chapters.sort()  # Sort alphabetically
        
        # Show original chapter names (with spaces)
        keyboard = []
        for ch in chapters:
            display_name = ch  # Use the original stored name
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

    # Admin subject selection
    if data.startswith("admin_sub_"):
        subject = data.replace("admin_sub_", "")
        admin_state["subject"] = subject
        keyboard = [
            get_back_button("admin_subjects"),
            [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
        ]
        query.edit_message_text(
            f"📘 *{subject.capitalize()} Selected*\n\n📝 Please send the *chapter name* (e.g., 'Electric Field and Charges'):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        admin_state["step"] = "chapter"
        return
    
    # Exit admin mode from callback
    if data == "exit_admin_mode":
        admin_state.clear()
        query.edit_message_text(
            "✅ *Exited Admin Mode*\n\nYou are now in user mode. Use /start to browse content.",
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
        chapters.sort()  # Sort alphabetically
        
        # Show original chapter names
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

    # User chapter selection - FIXED VERSION
    if data.startswith("user_ch_"):
        # Parse the callback data properly
        try:
            parts = data.split("_")
            if len(parts) >= 4:
                subject = parts[2]  # user_ch_physics_electric_field_and_charges
                chapter_encoded = "_".join(parts[3:])  # Handle multiple underscores
            else:
                # Try old format as fallback
                subject = data.split("_")[2] if len(data.split("_")) > 2 else ""
                chapter_encoded = data.split("_")[3] if len(data.split("_")) > 3 else ""
            
            print(f"🔍 DEBUG: user_ch_ parsed - subject: {subject}, chapter_encoded: {chapter_encoded}")
            
            if not subject or not chapter_encoded:
                query.edit_message_text("❌ Invalid chapter selection.")
                return
            
            # Find original chapter name
            original_chapter = find_original_chapter(subject, chapter_encoded)
            
            if not original_chapter:
                # Try to show what's in the database
                db = load_db()
                print(f"🔍 DEBUG: Database contents for {subject}: {db.get(subject, {})}")
                print(f"🔍 DEBUG: Looking for chapter matching: {chapter_encoded}")
                
                query.edit_message_text(
                    f"❌ Chapter not found.\n\nPlease try selecting the chapter again from the list.",
                    parse_mode="Markdown"
                )
                return
                
            # Create content type selection buttons
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

    # User content type selection - FIXED VERSION
    if data.startswith("user_type_"):
        try:
            parts = data.split("_")
            if len(parts) >= 5:
                subject = parts[2]
                chapter_encoded = parts[3]
                ctype = parts[4]
                
                print(f"🔍 DEBUG: user_type_ parsed - subject: {subject}, chapter_encoded: {chapter_encoded}, type: {ctype}")
                
                # Find original chapter name
                original_chapter = find_original_chapter(subject, chapter_encoded)
                
                if not original_chapter:
                    query.edit_message_text("❌ Chapter not found.")
                    return
                
                # Get file ID
                db = load_db()
                file_id = None
                if subject in db and original_chapter in db[subject]:
                    file_id = db[subject][original_chapter].get(ctype)
                
                if not file_id:
                    # Show content type selection again
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
                
                # Send the file
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
                    
                    # Send navigation options
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
            get_back_button("admin_subjects"),
            [InlineKeyboardButton("❌ Cancel & Exit", callback_data="exit_admin_mode")]
        ]
        query.edit_message_text(
            f"⬆️ *Upload {content_type_names.get(ctype, ctype)}*\n\nPlease send the file now:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def message_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    
    # Handle non-admin users
    if user_id != ADMIN_ID:
        # Allow commands
        if update.message.text and update.message.text.startswith('/'):
            return
        
        # Send warning for random messages
        update.message.reply_text(
            "⚠️ *Focus on Studies!*\n\nStop wasting time on unnecessary messages.\nUse */start* to access study materials.\n\n_Repeated messages may result in blocking._",
            parse_mode="Markdown"
        )
        return
    
    # ADMIN HANDLING
    if admin_state.get("step") == "chapter":
        chapter_name = update.message.text.strip()
        if not chapter_name:
            update.message.reply_text("❌ Please enter a valid chapter name.")
            return
            
        admin_state["chapter"] = chapter_name  # Store original name with spaces
        admin_state["step"] = "type"
        
        keyboard = [
            [InlineKeyboardButton("🎥 Lecture (MP4)", callback_data="admin_type_lecture")],
            [InlineKeyboardButton("📝 Notes (PDF)", callback_data="admin_type_notes")],
            [InlineKeyboardButton("📊 DPP (PDF)", callback_data="admin_type_dpp")],
            get_back_button("admin_subjects"),
            [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
        ]
        update.message.reply_text(
            f"📝 *Chapter:* {chapter_name}\n\nSelect content type to upload:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if admin_state.get("step") == "upload":
        subject = admin_state.get("subject")
        chapter = admin_state.get("chapter")  # Original name with spaces
        ctype = admin_state.get("ctype")
        
        if not all([subject, chapter, ctype]):
            update.message.reply_text(
                "❌ *Error: Missing data.*\nPlease start over with /vishal",
                parse_mode="Markdown"
            )
            admin_state.clear()
            return
        
        # Get file ID
        file_id = None
        if ctype == "lecture" and update.message.video:
            file_id = update.message.video.file_id
        elif ctype in ["notes", "dpp"] and update.message.document:
            file_id = update.message.document.file_id
        elif update.message.video:
            file_id = update.message.video.file_id
        elif update.message.document:
            file_id = update.message.document.file_id
        
        if not file_id:
            update.message.reply_text(
                f"❌ *Invalid File Type*\n\nFor *lectures*: Send MP4 video\nFor *notes/DPP*: Send PDF document",
                parse_mode="Markdown"
            )
            return
        
        # Save to database - store original chapter name
        db = load_db()
        db.setdefault(subject, {})
        db[subject].setdefault(chapter, {})  # Store with original name
        db[subject][chapter][ctype] = file_id
        save_db(db)
        
        # Print success message
        print(f"✅ SAVED: Subject='{subject}', Chapter='{chapter}', Type='{ctype}'")
        print(f"✅ Clean name for callback: '{clean_chapter_name(chapter)}'")
        
        # Success message
        content_type_names = {
            "lecture": "Lecture Video",
            "notes": "Notes",
            "dpp": "DPP"
        }
        
        update.message.reply_text(
            f"✅ *{content_type_names.get(ctype, ctype)} Saved Successfully!*\n\n"
            f"📘 *Subject:* {subject.capitalize()}\n"
            f"📖 *Chapter:* {chapter}\n"
            f"📁 *Type:* {content_type_names.get(ctype, ctype)}\n\n"
            f"✅ *Content is now visible to all users!*",
            parse_mode="Markdown"
        )
        
        # Show next options
        keyboard = [
            [InlineKeyboardButton(f"📤 Upload more for {chapter}", callback_data=f"admin_sub_{subject}")],
            get_back_button("admin_subjects"),
            [InlineKeyboardButton("❌ Exit Admin Mode", callback_data="exit_admin_mode")]
        ]
        update.message.reply_text(
            "📋 *What would you like to do next?*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Reset for next upload (keep subject)
        admin_state.clear()
        admin_state["subject"] = subject
        admin_state["step"] = "chapter"
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
    print("🔧 Commands: /start, /vishal (admin), /out (exit admin)")
    print("🐛 Debug mode: ON (shows callback data in console)")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
