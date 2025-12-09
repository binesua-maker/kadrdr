"""
Безопасное хранение API ключей
Создайте .env файл в корне проекта:

TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
BINANCE_API_KEY=your_binance_api_key_here
BINANCE_API_SECRET=your_binance_api_secret_here
"""

import os
from dotenv import load_dotenv

load_dotenv()

def get_telegram_token():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN не найден в .env файле")
    return token

def get_binance_credentials():
    api_key = os.getenv('BINANCE_API_KEY')
    api_secret = os.getenv('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        raise ValueError("Binance API ключи не найдены в .env файле")
    
    return api_key, api_secret