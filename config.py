import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
PROXY_URL = os.getenv("PROXY_URL")  # опционально, для обхода блокировок

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")
if not ADMIN_CHAT_ID:
    raise ValueError("ADMIN_CHAT_ID не найден в переменных окружения")

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)
except ValueError:
    raise ValueError("ADMIN_CHAT_ID должен быть числом (ID чата)")

# Проверяем доступность Telegram API
import urllib.request
import json
import sys

def check_telegram_api():
    """Проверяет доступность Telegram API и возвращает True/False"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        urllib.request.urlopen(url, timeout=5)
        return True
    except Exception:
        return False

if not check_telegram_api():
    if not PROXY_URL:
        print("⚠️ Telegram API недоступен напрямую.")
        print("Добавьте PROXY_URL в .env для подключения через прокси (SOCKS5).")
        print("Пример: PROXY_URL=socks5://user:pass@host:port")
        print("Или:   PROXY_URL=socks5://host:port")
    else:
        print(f"✅ Telegram API будет доступен через прокси: {PROXY_URL}")