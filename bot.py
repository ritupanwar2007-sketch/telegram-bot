import json
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
        "⚙️ *Admin Panel*\nSelect subject to manage:",
        parse_mode="Markdown",
        reply_markup=subject_keyboard("admin")
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

admin_state = {}

def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

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
        chapters = db[subject].keys()
        keyboard = [[InlineKeyboardButton(f"📖 {ch}", callback_data=f"user_ch_{subject}_{ch}")] for ch in chapters]
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
            chapter = " ".join(parts[1:])  # Join in case chapter has underscores
            keyboard = [
                [InlineKeyboardButton("🎥 Lectures", callback_data=f"user_type_{subject}_{chapter}_lecture")],
                [InlineKeyboardButton("📝 Notes", callback_data=f"user_type_{subject}_{chapter}_notes")],
                [InlineKeyboardButton("📊 DPP", callback_data=f"user_type_{subject}_{chapter}_dpp")],
            ]
            keyboard.append(get_back_button("chapters", subject))
            query.edit_message_text(
                f"📂 *{chapter}*\nSelect content type:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
        
    elif data == "back_admin_subjects":
        query.edit_message_text(
            "⚙️ *Admin Panel*\nSelect subject to manage:",
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
        ]
        query.edit_message_text(
            f"📘 *{subject.capitalize()} Selected*\n\n📝 Please send the *chapter name*:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        admin_state["step"] = "chapter"
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
        chapters = db[subject].keys()
        keyboard = [[InlineKeyboardButton(f"📖 {ch}", callback_data=f"user_ch_{subject}_{ch}")] for ch in chapters]
        keyboard.append(get_back_button("subjects"))
        query.edit_message_text(
            f"📂 *{subject.capitalize()} - Select Chapter:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # User chapter selection
    if data.startswith("user_ch_"):
        parts = data.split("_", 2)
        if len(parts) >= 3:
            subject = parts[1]
            chapter = parts[2]
            keyboard = [
                [InlineKeyboardButton("🎥 Lectures", callback_data=f"user_type_{subject}_{chapter}_lecture")],
                [InlineKeyboardButton("📝 Notes", callback_data=f"user_type_{subject}_{chapter}_notes")],
                [InlineKeyboardButton("📊 DPP", callback_data=f"user_type_{subject}_{chapter}_dpp")],
            ]
            keyboard.append(get_back_button("chapters", subject))
            query.edit_message_text(
                f"📂 *{chapter}*\nSelect content type:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    # User content type selection
    if data.startswith("user_type_"):
        parts = data.split("_")
        if len(parts) >= 5:
            subject = parts[2]
            chapter = parts[3]
            ctype = parts[4]
            
            db = load_db()
            file_id = db.get(subject, {}).get(chapter, {}).get(ctype)
            
            if not file_id:
                # Show error with options to try other content types
                keyboard = [
                    [InlineKeyboardButton("🎥 Lectures", callback_data=f"user_type_{subject}_{chapter}_lecture")],
                    [InlineKeyboardButton("📝 Notes", callback_data=f"user_type_{subject}_{chapter}_notes")],
                    [InlineKeyboardButton("📊 DPP", callback_data=f"user_type_{subject}_{chapter}_dpp")],
                ]
                keyboard.append(get_back_button("chapters", subject))
                
                content_type_names = {
                    "lecture": "Lecture Video",
                    "notes": "Notes PDF",
                    "dpp": "DPP (Daily Practice Problems)"
                }
                
                query.edit_message_text(
                    f"⚠️ *Content Not Available*\n\n{content_type_names.get(ctype, ctype)} for *{chapter}* is not uploaded yet.\n\nPlease select another content type:",
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
                        caption=f"🎥 *{chapter} - Lecture*\n\n_Enjoy your study!_ 📚",
                        parse_mode="Markdown"
                    )
                else:
                    doc_type = "Notes" if ctype == "notes" else "DPP"
                    context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=file_id,
                        caption=f"📄 *{chapter} - {doc_type}*\n\n_Happy Learning!_ ✨",
                        parse_mode="Markdown"
                    )
                
                # Send navigation options
                keyboard = [
                    get_back_button("types", f"{subject}_{chapter}"),
                    get_back_button("subjects")
                ]
                query.message.reply_text(
                    "✅ *Content Sent Successfully!*\n\nWhat would you like to do next?",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                
            except Exception as e:
                query.edit_message_text(
                    f"❌ *Error*\n\nFailed to send content. Please try again later.\n\n_Error: {str(e)}_",
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
            
        admin_state["chapter"] = chapter_name
        admin_state["step"] = "type"
        
        keyboard = [
            [InlineKeyboardButton("🎥 Lecture (MP4)", callback_data="admin_type_lecture")],
            [InlineKeyboardButton("📝 Notes (PDF)", callback_data="admin_type_notes")],
            [InlineKeyboardButton("📊 DPP (PDF)", callback_data="admin_type_dpp")],
            get_back_button("admin_subjects"),
        ]
        update.message.reply_text(
            f"📝 *Chapter:* {chapter_name}\n\nSelect content type to upload:",
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
        
        # Save to database
        db = load_db()
        db.setdefault(subject, {})
        db[subject].setdefault(chapter, {})
        db[subject][chapter][ctype] = file_id
        save_db(db)
        
        # Success message
        content_type_names = {
            "lecture": "Lecture Video",
            "notes": "Notes",
            "dpp": "DPP"
        }
        
        update.message.reply_text(
            f"✅ *{content_type_names.get(ctype, ctype)} Saved Successfully!*\n\n📘 *Subject:* {subject.capitalize()}\n📖 *Chapter:* {chapter}\n📁 *Type:* {content_type_names.get(ctype, ctype)}",
            parse_mode="Markdown"
        )
        
        # Show next options
        keyboard = [
            [InlineKeyboardButton(f"📤 Upload more for {chapter}", callback_data=f"admin_sub_{subject}")],
            get_back_button("admin_subjects"),
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
    dp.add_handler(CallbackQueryHandler(admin_type, pattern="^admin_type_"))
    dp.add_handler(CallbackQueryHandler(callback_handler))
    dp.add_handler(MessageHandler(Filters.all, message_handler))
    
    print("🤖 Bot is running...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
