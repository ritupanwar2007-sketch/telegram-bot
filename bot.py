from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
import config
from database import init_db
from handlers import *

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    print(f"Update {update} caused error {context.error}")

def main():
    # Initialize database
    init_db()
    
    # Create application
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Add conversation handler for admin add content
    admin_content_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(select_subject_content_handler, pattern='^subject_.*$'),
            CallbackQueryHandler(select_chapter_content_handler, pattern='^chapter_add_content_.*$'),
            CallbackQueryHandler(select_content_type_admin_handler, pattern='^add_content_type_.*$')
        ],
        states={
            SELECT_SUBJECT_CONTENT: [CallbackQueryHandler(select_subject_content_handler, pattern='^subject_.*$')],
            SELECT_CHAPTER_CONTENT: [CallbackQueryHandler(select_chapter_content_handler, pattern='^chapter_add_content_.*$')],
            SELECT_CONTENT_TYPE: [CallbackQueryHandler(select_content_type_admin_handler, pattern='^add_content_type_.*$')],
            ENTER_CONTENT_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_content_number_admin_handler)],
            SEND_CONTENT_FILE: [MessageHandler(filters.VIDEO | filters.Document.ALL, save_content_file_handler)]
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: u.message.reply_text("Operation cancelled."))]
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("help", help_command))
    
    application.add_handler(admin_content_conversation)
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, send_content_number))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chapter_name_input))
    application.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, save_content_file_handler))
    
    # Start bot
    print("🤖 Board Booster Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
