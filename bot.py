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

# /start 指令的處理函數
async def start(update: Update, context):
    await update.message.reply_text("請輸入看板")

# 處理用戶傳來的文字訊息
async def echo(update: Update, context):
    user_message = update.message.text.strip()
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
                
                # 使用 await 等待 response.text() 以獲取文本內容
                response_text = await response.text()  
    except Exception as e:
        print(f"發生錯誤：{e}")
        return ["發生錯誤，請確認看板名稱是否正確。"]

    # 這裡傳入的是獲取到的字符串內容
    soup = BeautifulSoup(response_text, 'html.parser')
    titles = soup.find_all('div', class_='title')

    messages = []
    for title in titles:
        if title.a:  # 確認標題存在
            messages.append(title.a.text.strip())
    
    if messages:
        return messages
    return ["無法擷取標題"]
# 發送訊息到 Telegram
async def send_message(message, chat_id):
    await bot.send_message(chat_id=chat_id, text=message)

# 定時執行的任務
async def job(chat_id, ptt_title):
    titles = await fetch_titles(ptt_title)
    message = "PTT {ptt_title} 最新文章標題：\n" + "\n".join(titles[:5]) 
    await send_message(message, chat_id)
    print("訊息已推送！")

# 設定排程 (每 30 分鐘執行一次)
def schedule_job(chat_id, ptt_title):
    schedule.every(30).minutes.do(lambda: asyncio.run(job(chat_id)))  # 使用 asyncio.run 運行異步的 job

# 設定機器人
def main():
    app = Application.builder().token(TOKEN).build()

    # 指令處理器
    app.add_handler(CommandHandler("start", start))

    # 文字訊息處理器
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))


    print("機器人啟動中...")

    # 啟動機器人
    loop = asyncio.get_event_loop()
    loop.create_task(app.run_polling())

    # 設定排程
    if CHAT_ID:
        schedule_job(CHAT_ID)
    else:
        print("未設定 CHAT_ID，請檢查 .env 檔案。")
    
    # 定期檢查排程
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()
   
