from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
import config
from database import init_db
from handlers import *

def main():
    # Initialize database
    init_db()
    
    # Create updater and dispatcher
    updater = Updater(token=config.BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Add conversation handler for admin
    admin_conversation = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(select_subject_content, pattern='^subject_'),
            CallbackQueryHandler(select_chapter_content, pattern='^chapter_add_content_'),
            CallbackQueryHandler(select_content_type_admin, pattern='^content_add_'),
            CallbackQueryHandler(add_chapter_name, pattern='^add_chapter$')
        ],
        states={
            SELECT_SUBJECT_CONTENT: [CallbackQueryHandler(select_subject_content, pattern='^subject_')],
            SELECT_CHAPTER_CONTENT: [CallbackQueryHandler(select_chapter_content, pattern='^chapter_add_content_')],
            SELECT_CONTENT_TYPE: [CallbackQueryHandler(select_content_type_admin, pattern='^content_add_')],
            ENTER_CONTENT_NUMBER: [MessageHandler(Filters.text & ~Filters.command, enter_content_number_admin)],
            SEND_CONTENT_FILE: [MessageHandler(Filters.video | Filters.document, save_content_file)],
            ENTER_CHAPTER: [MessageHandler(Filters.text & ~Filters.command, add_chapter_name)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Add handlers
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("admin", admin_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    dispatcher.add_handler(admin_conversation)
    
    dispatcher.add_handler(CallbackQueryHandler(callback_query_handler))
    
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, send_content_number))
    
    # Start bot
    print("🤖 Board Booster Bot is starting...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
