import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# 指定 .env 的路徑
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config/.env'))
load_dotenv(ENV_PATH)

# 確認 .env 是否存在
if not os.path.exists(ENV_PATH):
    raise FileNotFoundError(f".env 檔案不存在：{ENV_PATH}")

# 從環境變數中載入 Token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if TOKEN is None:
    raise ValueError("TELEGRAM_BOT_TOKEN 未正確載入，請檢查 .env 檔案的路徑或檔案內容。")

async def start(update: Update, context):
    await update.message.reply_text("你好！這是我的 Telegram 機器人！")

async def echo(update: Update, context):
    user_message = update.message.text
    await update.message.reply_text(f"你說：{user_message}")
    
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    print("機器人啟動中...")
    app.run_polling()

if __name__ == "__main__":
    main()
