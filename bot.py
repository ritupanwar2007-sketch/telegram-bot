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

def subject_keyboard(mode):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Physics", callback_data=f"{mode}_sub_physics")],
        [InlineKeyboardButton("Chemistry", callback_data=f"{mode}_sub_chemistry")],
        [InlineKeyboardButton("Maths", callback_data=f"{mode}_sub_maths")],
        [InlineKeyboardButton("English", callback_data=f"{mode}_sub_english")]
    ])

def admin(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return update.message.reply_text("Not admin")
    update.message.reply_text(
        "Admin Panel – Select subject:",
        reply_markup=subject_keyboard("admin")
    )

admin_state = {}

def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data
    query.answer()

    if data.startswith("admin_sub_"):
        subject = data.replace("admin_sub_", "")
        admin_state["subject"] = subject
        query.edit_message_text(f"Selected subject: {subject}\nSend chapter name:")
        admin_state["step"] = "chapter"
        return

    if data.startswith("user_sub_"):
        subject = data.replace("user_sub_", "")
        db = load_db()
        if subject not in db:
            return query.edit_message_text("No chapters yet.")
        chapters = db[subject].keys()
        keyboard = [[InlineKeyboardButton(ch, callback_data=f"user_ch_{subject}_{ch}")] for ch in chapters]
        query.edit_message_text("Select chapter:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("user_ch_"):
        _, subject, chapter = data.split("_", 2)
        keyboard = [
            [InlineKeyboardButton("Lectures", callback_data=f"user_type_{subject}_{chapter}_lecture")],
            [InlineKeyboardButton("Notes", callback_data=f"user_type_{subject}_{chapter}_notes")],
            [InlineKeyboardButton("DPP", callback_data=f"user_type_{subject}_{chapter}_dpp")],
        ]
        query.edit_message_text("Select content type:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if data.startswith("user_type_"):
        _, subject, chapter, ctype = data.split("_", 3)
        db = load_db()
        file_id = db.get(subject, {}).get(chapter, {}).get(ctype)
        if not file_id:
            return query.edit_message_text("No file uploaded.")
        if ctype == "lecture":
            context.bot.send_video(chat_id=query.message.chat_id, video=file_id)
        else:
            context.bot.send_document(chat_id=query.message.chat_id, document=file_id)
        return

def message_handler(update: Update, context: CallbackContext):
    user = update.message.from_user.id
    if user != ADMIN_ID:
        return

    if admin_state.get("step") == "chapter":
        admin_state["chapter"] = update.message.text
        admin_state["step"] = "type"
        keyboard = [
            [InlineKeyboardButton("Lecture (mp4)", callback_data="admin_type_lecture")],
            [InlineKeyboardButton("Notes (pdf)", callback_data="admin_type_notes")],
            [InlineKeyboardButton("DPP (pdf)", callback_data="admin_type_dpp")],
        ]
        update.message.reply_text("Select content type:", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    if admin_state.get("step") == "upload":
        subject = admin_state["subject"]
        chapter = admin_state["chapter"]
        ctype = admin_state["ctype"]
        db = load_db()
        db.setdefault(subject, {})
        db[subject].setdefault(chapter, {})
        if update.message.video:
            file_id = update.message.video.file_id
        elif update.message.document:
            file_id = update.message.document.file_id
        else:
            return update.message.reply_text("Upload mp4 or pdf only.")
        db[subject][chapter][ctype] = file_id
        save_db(db)
        update.message.reply_text("Saved successfully!")
        admin_state.clear()

def admin_type(update: Update, context: CallbackContext):
    data = update.callback_query.data
    query = update.callback_query
    if not data.startswith("admin_type_"):
        return
    ctype = data.replace("admin_type_", "")
    admin_state["ctype"] = ctype
    admin_state["step"] = "upload"
    query.edit_message_text(f"Send your {ctype} file now:")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("vishal", admin))
    dp.add_handler(CallbackQueryHandler(admin_type, pattern="admin_type_"))
    dp.add_handler(CallbackQueryHandler(callback_handler))
    dp.add_handler(MessageHandler(Filters.all, message_handler))
    updater.start_polling()
    updater.idle()

main()
