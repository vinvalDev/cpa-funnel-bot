import logging
import os
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.ext import CallbackContext
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from tinydb import TinyDB, Query
import json

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Config ---
TOKEN = "YOUR_BOT_TOKEN"
GROUP_LINK = "https://t.me/yourgroup"
FOLLOW_UP_DELAY_MINUTES = 1440  # Delay before DM follow-up

# --- Database ---
db = TinyDB("leads.json")
UserTable = Query()
scheduler = BackgroundScheduler()
scheduler.start()

# --- Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if not db.contains(UserTable.user_id == user_id):
        db.insert({"user_id": user_id, "name": user.first_name, "timestamp": datetime.utcnow().isoformat()})

        await update.message.reply_text(
            f"Hey {user.first_name}, welcome! 🎯\nHere’s what we have for you..."
        )
        await update.message.reply_text(f"Join our group here: {GROUP_LINK}")

        # Schedule follow-up
        followup_time = datetime.utcnow() + timedelta(minutes=FOLLOW_UP_DELAY_MINUTES)
        scheduler.add_job(
            send_followup,
            trigger=DateTrigger(run_date=followup_time),
            args=[context.bot, user_id],
            id=str(user_id),
            replace_existing=True
        )
    else:
        await update.message.reply_text("You're already registered! 💬")

async def send_followup(bot, user_id):
    user_data = db.get(UserTable.user_id == user_id)
    if user_data:
        try:
            await bot.send_message(chat_id=user_id, text="👋 Just checking in! Ready to take the next step? Join the group or reach out if you have questions.")
        except Exception as e:
            logger.warning(f"Could not send follow-up to {user_id}: {e}")

async def lead_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = len(db)
    await update.message.reply_text(f"📊 Total leads: {count}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        message = ' '.join(context.args)
        failed = 0
        for user in db:
            try:
                await context.bot.send_message(chat_id=user['user_id'], text=message)
            except:
                failed += 1
        await update.message.reply_text(f"✅ Broadcast sent! Failed to send to {failed} users.")
    else:
        await update.message.reply_text("Usage: /broadcast Your message here")

# --- Main ---

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leadcount", lead_count))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.run_polling()

if __name__ == '__main__':
    main()
