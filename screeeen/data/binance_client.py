import ccxt
import pandas as pd
from typing import List, Optional
from loguru import logger
from config.api_keys import get_binance_credentials


class BinanceDataClient:
    """Клиент для работы с Binance API"""

    def __init__(self):
        api_key, api_secret = get_binance_credentials()

        self.exchange = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })

        # Список стейблкоинов для исключения
        self.stablecoins = [
            'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD', 'USDP', 'USDD',
            'FDUSD', 'PYUSD', 'GUSD', 'PAX', 'SUSD', 'FRAX', 'LUSD',
            'USDK', 'USDJ', 'USDN', 'UST', 'CUSD', 'TRIBE', 'FEI',
            'EURT', 'EUROC', 'AEUR', 'EURS'
        ]

    async def get_top_coins(self, limit: int = 100) -> List[str]:
        """Получить топ N монет по объему торгов (исключая стейблкоины)"""
        try:
            # Загружаем рынки
            markets = self.exchange.load_markets()

            # Получаем тикеры с 24ч объемом
            tickers = self.exchange.fetch_tickers()

            # Фильтруем только USDT пары
            usdt_pairs = []
            for symbol, ticker in tickers.items():
                if '/USDT' in symbol and ticker.get('quoteVolume'):
                    base_currency = symbol.split('/')[0]

                    # Исключаем стейблкоины
                    if base_currency not in self.stablecoins:
                        usdt_pairs.append({
                            'symbol': symbol,
                            'volume': ticker['quoteVolume']
                        })

            # Сортируем по объему и берем топ N
            usdt_pairs.sort(key=lambda x: x['volume'], reverse=True)
            top_symbols = [pair['symbol'] for pair in usdt_pairs[:limit]]

            logger.info(f"Получено {len(top_symbols)} монет для анализа (без стейблкоинов)")
            return top_symbols

        except Exception as e:
            logger.error(f"Ошибка получения топ монет: {e}")
            return []

    async def get_ohlcv(self, symbol: str, timeframe: str = '15m', limit: int = 500) -> Optional[pd.DataFrame]:
        """Получить OHLCV данные для символа"""
        try:
            # Проверяем что символ не стейблкоин
            base_currency = symbol.split('/')[0]
            if base_currency in self.stablecoins:
                logger.debug(f"Пропускаем стейблкоин: {symbol}")
                return None

            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            if not ohlcv:
                return None

            # Преобразуем в DataFrame
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)

            return df

        except Exception as e:
            logger.error(f"Ошибка получения OHLCV для {symbol}: {e}")
            return None

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Получить текущую цену символа"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get('last')
        except Exception as e:
            logger.error(f"Ошибка получения цены {symbol}: {e}")
            return None

    async def get_24h_volume(self, symbol: str) -> Optional[float]:
        """Получить 24ч объем торгов"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get('quoteVolume')
        except Exception as e:
            logger.error(f"Ошибка получения объема {symbol}: {e}")
            return None

    def is_stablecoin(self, symbol: str) -> bool:
        """Проверить является ли монета стейблкоином"""
        base_currency = symbol.split('/')[0]
        return base_currency in self.stablecoins