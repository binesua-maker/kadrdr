import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

# Admin Settings (NEW)
ADMIN_USER_IDS = [int(x) for x in os.getenv('ADMIN_USER_IDS', '').split(',') if x.strip()]

# Binance Settings
BINANCE_TESTNET = False
TOP_COINS_LIMIT = 100
BASE_CURRENCY = 'USDT'

# Scanning Settings
SCAN_INTERVAL = int(os.getenv('SCAN_INTERVAL', 300))  # секунды (5 минут)
TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']
DEFAULT_TIMEFRAME = '15m'

# Multi-Timeframe Settings (NEW)
MTF_TIMEFRAMES = ['15m', '1h', '4h', '1d']

# Analysis Parameters
MIN_VOLUME_24H = int(os.getenv('MIN_VOLUME_24H', 1000000))  # минимальный объем в USD
MIN_PRICE_CHANGE = float(os.getenv('MIN_PRICE_CHANGE', 2.0))    # минимальное изменение цены %
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70

# Smart Money Concepts
FVG_MIN_SIZE = 0.5        # минимальный размер имбаланса в %
ORDER_BLOCK_LOOKBACK = 20  # свечей для поиска Order Blocks
LIQUIDITY_THRESHOLD = 1.5  # множитель для определения liquidity sweep

# Signal Types
SIGNAL_TYPES = {
    'structure_break': '🔨 Слом структуры',
    'level_approach': '📍 Поджим к уровню',
    'breakout': '🚀 Пробой',
    'false_breakout': '⚠️ Ложный пробой',
    'imbalance': '⚡ Имбаланс (FVG)',
    'order_block': '🎯 Order Block',
    'liquidity_sweep': '💧 Liquidity Sweep',
    'divergence': '📊 Дивергенция',
    'pattern': '📐 Паттерн',
    'volume_spike': '📢 Объемный всплеск',
    'confluence': '⭐ Зона совпадения'
}

# Display Settings
SHOW_CONFLUENCE = os.getenv('SHOW_CONFLUENCE', 'true').lower() == 'true'
SHOW_INDIVIDUAL_SIGNALS = True  # Показывать отдельные сигналы
MAX_SIGNALS_PER_COIN = int(os.getenv('MAX_SIGNALS_PER_COIN', 10))  # Максимум сигналов на одну монету

# Chart Settings
CHART_WIDTH = 1200
CHART_HEIGHT = 600
CHART_STYLE = 'charles'

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///screener.db')

# Redis Settings (NEW)
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = 'logs/screener.log'

# Alert Settings (NEW)
ALERT_CHECK_INTERVAL = 10  # секунды между проверками алертов

# Portfolio Settings (NEW)
PORTFOLIO_TRACK_PERFORMANCE = True

# Performance Tracking (NEW)
TRACK_SIGNAL_PERFORMANCE = True
PERFORMANCE_CHECK_INTERVALS = [1, 4, 24]  # часы