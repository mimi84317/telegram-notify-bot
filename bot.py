import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Bot
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import schedule
import time
import asyncio
import aiohttp 

# 指定 .env 的路徑
ENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../config/.env'))
load_dotenv(ENV_PATH)

# 確認 .env 是否存在
if not os.path.exists(ENV_PATH):
    raise FileNotFoundError(f".env 檔案不存在：{ENV_PATH}")

# 從 .env 檔案中取得環境變數
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")  # 推播的聊天室 ID

if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN 未正確載入，請檢查 .env 檔案。")

if not CHAT_ID:
    raise ValueError("TELEGRAM_CHAT_ID 未正確載入，請檢查 .env 檔案。")

# 初始化 Telegram Bot
bot = Bot(token=TOKEN)
scheduled_ptt_title = None  # 儲存目前設定的 PTT 看板名稱

# /start 指令的處理函數
async def start(update: Update, context):
    await update.message.reply_text("歡迎使用 PTT 機器人！請輸入看板名稱開始查詢最新文章。")

# 處理用戶傳來的文字訊息
async def echo(update: Update, context):
    global scheduled_ptt_title
    user_message = update.message.text.strip()
    scheduled_ptt_title = user_message  # 更新目前的看板名稱
    titles = await fetch_titles(ptt_title=user_message)
    message = f"看板 {user_message} 最新文章標題：\n" + "\n".join(titles)
    await update.message.reply_text(message)

# 爬取 PTT 看板的標題
async def fetch_titles(ptt_title):
    url = f"https://www.ptt.cc/bbs/{ptt_title}/index.html"

    try:
        async with aiohttp.ClientSession(cookies={'over18': '1'}) as session:
            async with session.get(url) as response:
                if response.status == 404:
                    return [f"看板 {ptt_title} 不存在，請確認名稱。"]

                response_text = await response.text()  
    except Exception as e:
        print(f"發生錯誤：{e}")
        return ["發生錯誤，請確認看板名稱是否正確。"]

    soup = BeautifulSoup(response_text, 'html.parser')
    titles = soup.find_all('div', class_='title')

    messages = []
    for title in titles:
        if title.a:  
            messages.append(title.a.text.strip())

    if messages:
        return messages
    return ["無法擷取標題"]

# 發送訊息到 Telegram
async def send_message(message, chat_id):
    await bot.send_message(chat_id=chat_id, text=message)

# 定時執行的任務
async def job(chat_id):
    if not scheduled_ptt_title:
        return  
    titles = await fetch_titles(scheduled_ptt_title)
    message = f"PTT {scheduled_ptt_title} 最新文章標題：\n" + "\n".join(titles)
    await send_message(message, chat_id)
    print("訊息已推送！")

# 包裝 schedule 的非同步函數
async def run_scheduler():
    while True:
        schedule.run_pending()
        await asyncio.sleep(1)  # 每秒檢查一次排程

# 設定排程 ( 每 30 分鐘執行一次 )
def schedule_job(chat_id):
    schedule.every(1).minutes.do(lambda: asyncio.create_task(job(chat_id)))

# 設定機器人
async def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    print("機器人啟動中...")

    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    # 啟動排程
    if CHAT_ID:
        schedule_job(CHAT_ID)
        asyncio.create_task(run_scheduler())

    # 保持機器人運行
    await asyncio.Event().wait()


if __name__ == "__main__":
    # 啟動 Telegram Bot
    asyncio.run(main())
