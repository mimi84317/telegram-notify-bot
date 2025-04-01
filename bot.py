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
latest_post_urls = set()  # 記錄已推送過的文章網址

# /start 指令的處理函數
async def start(update: Update, context):
    await update.message.reply_text("\u6b61\u8fce\u4f7f\u7528 PTT \u6a5f\u5668\u4eba\uff01\u8acb\u8f38\u5165\u770b\u677f\u540d\u7a31\u958b\u59cb\u67e5\u8a62\u6700\u65b0\u6587\u7ae0\u3002")

# 處理用戶傳來的文字訊息
async def echo(update: Update, context):
    global scheduled_ptt_title
    user_message = update.message.text.strip()
    scheduled_ptt_title = user_message  # 更新目前的看板名稱
    titles = await fetch_titles(ptt_title=user_message)
    message = f"看板 {user_message} 最新文章：\n" + "\n".join(titles)
    await update.message.reply_text(message)

# 爬取 PTT 看板的標題、作者、發文時間、網址
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
    titles = soup.find_all('div', class_='r-ent')
    messages = []
    
    global latest_post_urls
    new_post_urls = set()
    
    for entry in titles:
        title_tag = entry.find('div', class_='title').a
        if title_tag:
            title = title_tag.text.strip()
            post_url = f"https://www.ptt.cc{title_tag['href']}"
            new_post_urls.add(post_url)
            if post_url in latest_post_urls:
                continue  # 跳過已推送的文章
            
            async with aiohttp.ClientSession(cookies={'over18': '1'}) as session:
                async with session.get(post_url) as response:
                    post_soup = BeautifulSoup(await response.text(), 'html.parser')
                    meta_info = post_soup.find_all('span', class_='article-meta-value')
                    date = meta_info[3].text.strip() if len(meta_info) > 3 else "未知"
            
            messages.append(f"標題: {title}\n時間: {date}\n網址: {post_url}\n")
    
    latest_post_urls = new_post_urls
    return messages if messages else ["沒有新的文章"]

# 發送訊息到 Telegram
async def send_message(message, chat_id):
    await bot.send_message(chat_id=chat_id, text=message)

# 設定排程 ( 每 30 分鐘執行一次 )
def schedule_job(chat_id):
    schedule.every(30).minutes.do(lambda: asyncio.create_task(job(chat_id)))

# 設定機器人
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    print("Telegram 機器人已啟動...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    schedule_job(CHAT_ID)
    asyncio.run(main())
