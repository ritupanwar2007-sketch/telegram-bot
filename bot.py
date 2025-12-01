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
        "Hello! I am Board Booster Bot created by Vishal.\nChoose subject:",
        reply_markup=subject_keyboard("user")
    )

def admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return update.message.reply_text("Not admin")
    update.message.reply_text(
        "Admin Panel – Select subject:",
        reply_markup=subject_keyboard("admin")
    )

def subject_keyboard(mode):
    keyboard = [
        [InlineKeyboardButton("Physics", callback_data=f"{mode}_sub_physics")],
        [InlineKeyboardButton("Chemistry", callback_data=f"{mode}_sub_chemistry")],
        [InlineKeyboardButton("Maths", callback_data=f"{mode}_sub_maths")],
        [InlineKeyboardButton("English", callback_data=f"{mode}_sub_english")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_button(back_to, data=None):
    """Create a back button"""
    if back_to == "subjects":
        return [InlineKeyboardButton("← Back to Subjects", callback_data="back_subjects")]
    elif back_to == "chapters":
        return [InlineKeyboardButton("← Back to Chapters", callback_data=f"back_chapters_{data}")]
    elif back_to == "types":
        return [InlineKeyboardButton("← Back to Content Types", callback_data=f"back_types_{data}")]
    elif back_to == "admin_subjects":
        return [InlineKeyboardButton("← Back to Admin Subjects", callback_data="back_admin_subjects")]

admin_state = {}

def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

    # Handle back buttons
    if data == "back_subjects":
        query.edit_message_text(
            "Choose subject:",
            reply_markup=subject_keyboard("user")
        )
        return
        
    elif data.startswith("back_chapters_"):
        subject = data.replace("back_chapters_", "")
        db = load_db()
        if subject not in db:
            return query.edit_message_text("No chapters yet.")
        chapters = db[subject].keys()
        keyboard = [[InlineKeyboardButton(ch, callback_data=f"user_ch_{subject}_{ch}")] for ch in chapters]
        keyboard.append(get_back_button("subjects"))
        query.edit_message_text(
            f"Select chapter for {subject}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
        
    elif data.startswith("back_types_"):
        parts = data.replace("back_types_", "").split("_")
        if len(parts) >= 2:
            subject = parts[0]
            chapter = parts[1]
            keyboard = [
                [InlineKeyboardButton("Lectures", callback_data=f"user_type_{subject}_{chapter}_lecture")],
                [InlineKeyboardButton("Notes", callback_data=f"user_type_{subject}_{chapter}_notes")],
                [InlineKeyboardButton("DPP", callback_data=f"user_type_{subject}_{chapter}_dpp")],
            ]
            keyboard.append(get_back_button("chapters", subject))
            query.edit_message_text(
                f"Select content type for {chapter}:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return
        
    elif data == "back_admin_subjects":
        query.edit_message_text(
            "Admin Panel – Select subject:",
            reply_markup=subject_keyboard("admin")
        )
        return

    # Admin subject selection
    if data.startswith("admin_sub_"):
        subject = data.replace("admin_sub_", "")
        admin_state["subject"] = subject
        keyboard = [
            [InlineKeyboardButton("← Back to Admin Subjects", callback_data="back_admin_subjects")],
        ]
        query.edit_message_text(
            f"Selected subject: {subject}\nSend chapter name:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        admin_state["step"] = "chapter"
        return

    # User subject selection
    if data.startswith("user_sub_"):
        subject = data.replace("user_sub_", "")
        db = load_db()
        if subject not in db or not db[subject]:
            return query.edit_message_text("No chapters yet for this subject.")
        chapters = db[subject].keys()
        keyboard = [[InlineKeyboardButton(ch, callback_data=f"user_ch_{subject}_{ch}")] for ch in chapters]
        keyboard.append(get_back_button("subjects"))
        query.edit_message_text(
            f"Select chapter for {subject}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # User chapter selection
    if data.startswith("user_ch_"):
        _, subject, chapter = data.split("_", 2)
        keyboard = [
            [InlineKeyboardButton("Lectures", callback_data=f"user_type_{subject}_{chapter}_lecture")],
            [InlineKeyboardButton("Notes", callback_data=f"user_type_{subject}_{chapter}_notes")],
            [InlineKeyboardButton("DPP", callback_data=f"user_type_{subject}_{chapter}_dpp")],
        ]
        keyboard.append(get_back_button("chapters", subject))
        query.edit_message_text(
            f"Select content type for {chapter}:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # User content type selection
    if data.startswith("user_type_"):
        _, subject, chapter, ctype = data.split("_", 3)
        db = load_db()
        file_id = db.get(subject, {}).get(chapter, {}).get(ctype)
        if not file_id:
            query.edit_message_text("No file uploaded for this content type.")
            
            # Show content types again with back button
            keyboard = [
                [InlineKeyboardButton("Lectures", callback_data=f"user_type_{subject}_{chapter}_lecture")],
                [InlineKeyboardButton("Notes", callback_data=f"user_type_{subject}_{chapter}_notes")],
                [InlineKeyboardButton("DPP", callback_data=f"user_type_{subject}_{chapter}_dpp")],
            ]
            keyboard.append(get_back_button("chapters", subject))
            query.message.reply_text(
                f"No file uploaded for {ctype} in {chapter}.\nPlease select another content type:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
        if ctype == "lecture":
            context.bot.send_video(chat_id=query.message.chat_id, video=file_id)
        else:
            context.bot.send_document(chat_id=query.message.chat_id, document=file_id)
        
        # Send back button after sending file
        keyboard = [
            [InlineKeyboardButton("← Back to Content Types", callback_data=f"back_types_{subject}_{chapter}")],
            [InlineKeyboardButton("← Back to Subjects", callback_data="back_subjects")]
        ]
        query.message.reply_text(
            "What would you like to do next?",
            reply_markup=InlineKeyboardMarkup(keyboard)
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
        
        keyboard = [
            [InlineKeyboardButton("← Cancel Upload", callback_data="back_admin_subjects")],
        ]
        query.edit_message_text(
            f"Send your {ctype} file now:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

def message_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    
    # If user is not admin, show warning message
    if user_id != ADMIN_ID:
        # Check if it's a command (like /start)
        if update.message.text and update.message.text.startswith('/'):
            return  # Let command handlers handle it
            
        # Send warning message for any other text
        update.message.reply_text("⚠️ Focus on your studies! Stop wasting time on unnecessary messages or you might get blocked. Use /start to access study materials.")
        return
    
    # Admin handling continues here
    if admin_state.get("step") == "chapter":
        admin_state["chapter"] = update.message.text
        admin_state["step"] = "type"
        keyboard = [
            [InlineKeyboardButton("Lecture (mp4)", callback_data="admin_type_lecture")],
            [InlineKeyboardButton("Notes (pdf)", callback_data="admin_type_notes")],
            [InlineKeyboardButton("DPP (pdf)", callback_data="admin_type_dpp")],
            [InlineKeyboardButton("← Cancel", callback_data="back_admin_subjects")],
        ]
        update.message.reply_text(
            f"Chapter: {update.message.text}\nSelect content type:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if admin_state.get("step") == "upload":
        subject = admin_state.get("subject")
        chapter = admin_state.get("chapter")
        ctype = admin_state.get("ctype")
        
        if not all([subject, chapter, ctype]):
            update.message.reply_text("Error: Missing data. Start over with /vishal")
            admin_state.clear()
            return
            
        db = load_db()
        db.setdefault(subject, {})
        db[subject].setdefault(chapter, {})
        
        # Get file_id based on file type
        if ctype == "lecture" and update.message.video:
            file_id = update.message.video.file_id
        elif ctype in ["notes", "dpp"] and update.message.document:
            file_id = update.message.document.file_id
        else:
            # For backward compatibility, try to get any file
            if update.message.video:
                file_id = update.message.video.file_id
            elif update.message.document:
                file_id = update.message.document.file_id
            else:
                update.message.reply_text("Please send a video (mp4) for lectures or document (pdf) for notes/DPP.")
                return
        
        # Save to database
        db[subject][chapter][ctype] = file_id
        save_db(db)
        
        update.message.reply_text(f"✅ {ctype.capitalize()} saved successfully for {subject} - {chapter}!")
        
        # Show options after successful upload
        keyboard = [
            [InlineKeyboardButton("Upload another file for same chapter", callback_data=f"admin_sub_{subject}")],
            [InlineKeyboardButton("Go to Admin Panel", callback_data="back_admin_subjects")],
        ]
        update.message.reply_text(
            "What would you like to do next?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Reset state but keep subject for convenience
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
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
