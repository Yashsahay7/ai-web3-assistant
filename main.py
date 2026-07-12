# main.py
# Clean async version

import utils.session
import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from config import TELEGRAM_TOKEN
from bot_router import route_message
from smart_responder import clear_user_memory
from token_optimizer import get_usage_report
from vector_cache import cache

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ─────────────────────────────────────────
# COMMANDS
# ─────────────────────────────────────────
async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    name = update.message.from_user.first_name
    await update.message.reply_text(
        f"👋 Hello {name}!\n\n"
        f"I am your AI + Web3 Assistant!\n\n"
        f"💰 Crypto prices\n"
        f"👛 Wallet balances\n"
        f"📋 Transaction history\n"
        f"⛽ Gas fees\n"
        f"📚 Web3 explanations\n\n"
        f"Just ask me anything!"
    )

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.message.reply_text(
        "📖 *Examples:*\n\n"
        "`Bitcoin price`\n"
        "`What is ETH worth?`\n"
        "`Gas fees`\n"
        "`Market overview`\n"
        "`Check wallet 0x123...`\n"
        "`What is DeFi?`\n"
        "`Explain smart contracts`\n\n"
        "/clear - Reset conversation\n"
        "/stats - Token usage stats",
        parse_mode='Markdown'
    )

async def clear_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    await clear_user_memory(
        update.message.chat_id
    )
    await update.message.reply_text(
        "🗑️ Conversation cleared!"
    )

async def stats_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    report = get_usage_report()
    stats = cache.get_stats()
    await update.message.reply_text(
        f"{report}\n\n"
        f"*Cache:*\n"
        f"Entries: `{stats['total_entries']}`",
        parse_mode='Markdown'
    )

# ─────────────────────────────────────────
# MESSAGE HANDLER
# ─────────────────────────────────────────
async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    
    message = update.message.text
    name = update.message.from_user.first_name
    chat_id = update.message.chat_id
    
    print(f"\n👤 {name}: {message}")
    
    # Show typing
    await context.bot.send_chat_action(
        chat_id=chat_id,
        action="typing"
    )
    
    try:
        # Fully async route
        response = await route_message(
            message, chat_id
        )
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        response = "❌ Something went wrong!"
    
    await update.message.reply_text(
        response,
        parse_mode='Markdown'
    )

async def error_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    print(f"❌ Error: {context.error}")

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
def main() -> None:
    print("🚀 Starting bot...")
    
    app = Application.builder().token(
        TELEGRAM_TOKEN
    ).build()
    
    app.add_handler(
        CommandHandler("start", start_command)
    )
    app.add_handler(
        CommandHandler("help", help_command)
    )
    app.add_handler(
        CommandHandler("clear", clear_command)
    )
    app.add_handler(
        CommandHandler("stats", stats_command)
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message
        )
    )
    app.add_error_handler(error_handler)
    
    print("✅ Bot running!")
    
    app.run_polling(
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == '__main__':
    main()