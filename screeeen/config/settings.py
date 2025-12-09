import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

# Binance Settings
BINANCE_TESTNET = False
TOP_COINS_LIMIT = 100
BASE_CURRENCY = 'USDT'

# Scanning Settings
SCAN_INTERVAL = 300  # секунды (5 минут)
TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']
DEFAULT_TIMEFRAME = '15m'

# Analysis Parameters
MIN_VOLUME_24H = 1000000  # минимальный объем в USD
MIN_PRICE_CHANGE = 2.0    # минимальное изменение цены %
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
SHOW_CONFLUENCE = False  # Показывать ли объединенные сигналы confluence
SHOW_INDIVIDUAL_SIGNALS = True  # Показывать отдельные сигналы
MAX_SIGNALS_PER_COIN = 10  # Максимум сигналов на одну монету

# Chart Settings
CHART_WIDTH = 1200
CHART_HEIGHT = 600
CHART_STYLE = 'charles'

# Database
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///screener.db')

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/screener.log'