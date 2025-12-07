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
            ENTER_CONTENT_NUMBER: [MessageHandler(Filters.text & ~Filters.command, enter_content_number_admin_handler)],
            SEND_CONTENT_FILE: [MessageHandler(Filters.video | Filters.document, save_content_file_handler)]
        },
        fallbacks=[CommandHandler('cancel', lambda u, c: u.message.reply_text("Operation cancelled."))]
    )
    
    # Add handlers
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("admin", admin_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    dispatcher.add_handler(admin_content_conversation)
    
    # Add callback query handler
    dispatcher.add_handler(CallbackQueryHandler(callback_query_handler))
    
    # Add message handlers
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, send_content_number))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_chapter_name_input))
    dispatcher.add_handler(MessageHandler(Filters.video | Filters.document, save_content_file_handler))
    
    # Start bot
    print("🤖 Board Booster Bot is starting...")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
