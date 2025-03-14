import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from telegram import Bot
import schedule
import time
import asyncio

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

# 初始化 Telegram Bot
bot = Bot(token=TOKEN)

# 獲取 chat_id
async def get_chat_id():
    updates = await bot.get_updates()  # 使用 await 來等待異步操作完成
    for update in updates:
        print(f"Chat ID: {update.message.chat.id}")  # 打印出 chat_id
        return update.message.chat.id  # 返回第一個聊天的 chat_id

# 爬取 PTT NSwitch 看板的標題
def fetch_titles():
    url = "https://www.ptt.cc/bbs/NSwitch/index.html"

    try:
        response = requests.get(url, cookies={'over18': '1'})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"發生錯誤：{e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
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
async def job(chat_id):
    titles = fetch_titles()
    message = "PTT NSwitch 最新文章標題：\n" + "\n".join(titles[:5])  # 只推播前 5 筆
    await send_message(message, chat_id)
    print("訊息已推送！")

# 設定排程 (每 30 分鐘執行一次)
def schedule_job(chat_id):
    schedule.every(30).minutes.do(lambda: asyncio.run(job(chat_id)))  # 使用 asyncio.run 運行異步的 job

if __name__ == "__main__":
    print("機器人啟動中...")
    chat_id = asyncio.run(get_chat_id())  # 獲取 chat_id
    print(f"使用的 CHAT_ID: {chat_id}")
    schedule_job(chat_id)  # 設定排程
    while True:
        schedule.run_pending()
        time.sleep(1)
