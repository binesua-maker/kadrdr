"""
Data Processor - Полностью переписанная версия v2.0
Обработка и анализ рыночных данных с расширенными индикаторами
"""
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
from loguru import logger
import asyncio
from datetime import datetime, timedelta
import ccxt

from utils.rate_limiter import binance_limiter
from utils.cache import cache


class DataProcessor:
    """Обработка и нормализация данных с Binance"""

    def __init__(self):
        self.exchange = None
        self._initialized = False

    def _init_exchange(self):
        """Ленивая инициализация биржи"""
        if not self._initialized:
            try:
                self.exchange = ccxt.binance({
                    'enableRateLimit': True,
                    'options': {'defaultType': 'spot'}
                })
                self._initialized = True
                logger.info("DataProcessor: Exchange инициализирована")
            except Exception as e:
                logger.error(f"Ошибка инициализации биржи: {e}")

    async def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = '15m',
        limit: int = 200,
        use_cache: bool = True
    ) -> Optional[pd.DataFrame]:
        """
        Получить OHLCV данные с кэшированием
        
        Args:
            symbol: Символ монеты
            timeframe: Таймфрейм
            limit: Количество свечей
            use_cache: Использовать кэш
        
        Returns:
            DataFrame с OHLCV данными
        """
        # Проверяем кэш
        cache_key = f"ohlcv:{symbol}:{timeframe}:{limit}"
        
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                try:
                    return pd.DataFrame(cached)
                except Exception as e:
                    logger.debug(f"Ошибка чтения из кэша: {e}")

        # Ленивая инициализация
        if not self._initialized:
            self._init_exchange()

        if not self.exchange:
            return None

        try:
            # Rate limiting
            await binance_limiter.acquire('binance')

            # Получаем данные
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

            if not ohlcv:
                return None

            # Преобразуем в DataFrame
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )

            # Преобразуем timestamp
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

            # Сохраняем в кэш
            if use_cache:
                cache.set(cache_key, df.to_dict('records'), ttl=60)

            return df

        except Exception as e:
            logger.error(f"Ошибка получения OHLCV для {symbol}: {e}")
            return None

    async def get_ticker(self, symbol: str, use_cache: bool = True) -> Optional[Dict]:
        """Получить тикер с кэшированием"""
        cache_key = f"ticker:{symbol}"

        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                return cached

        if not self._initialized:
            self._init_exchange()

        if not self.exchange:
            return None

        try:
            await binance_limiter.acquire('binance')
            ticker = self.exchange.fetch_ticker(symbol)

            if use_cache:
                cache.set(cache_key, ticker, ttl=10)

            return ticker

        except Exception as e:
            logger.error(f"Ошибка получения тикера для {symbol}: {e}")
            return None

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Добавить расширенный набор технических индикаторов
        Включая все стандартные + новые: Stochastic RSI, OBV, VWAP
        """
        if df is None or len(df) < 20:
            return df

        try:
            # === Moving Averages ===
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_200'] = df['close'].rolling(window=200).mean()

            df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
            df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
            df['ema_55'] = df['close'].ewm(span=55, adjust=False).mean()

            # === RSI ===
            df['rsi'] = self.calculate_rsi(df['close'], period=14)

            # === Stochastic RSI (NEW) ===
            stoch_rsi = self.calculate_stochastic_rsi(df['close'])
            df['stoch_rsi_k'] = stoch_rsi['k']
            df['stoch_rsi_d'] = stoch_rsi['d']

            # === MACD ===
            macd_data = self.calculate_macd(df['close'])
            df['macd'] = macd_data['macd']
            df['macd_signal'] = macd_data['signal']
            df['macd_histogram'] = macd_data['histogram']

            # === Bollinger Bands ===
            bb_data = self.calculate_bollinger_bands(df['close'])
            df['bb_upper'] = bb_data['upper']
            df['bb_middle'] = bb_data['middle']
            df['bb_lower'] = bb_data['lower']

            # === ATR ===
            df['atr'] = self.calculate_atr(df)

            # === Volume Indicators ===
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']

            # === OBV - On Balance Volume (NEW) ===
            df['obv'] = self.calculate_obv(df)

            # === VWAP - Volume Weighted Average Price (NEW) ===
            df['vwap'] = self.calculate_vwap(df)

            # === Stochastic ===
            stoch_data = self.calculate_stochastic(df)
            df['stoch_k'] = stoch_data['k']
            df['stoch_d'] = stoch_data['d']

            # === ADX - Average Directional Index ===
            adx_data = self.calculate_adx(df)
            df['adx'] = adx_data['adx']
            df['plus_di'] = adx_data['plus_di']
            df['minus_di'] = adx_data['minus_di']

            return df

        except Exception as e:
            logger.error(f"Ошибка добавления индикаторов: {e}")
            return df

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """Расчет RSI"""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def calculate_stochastic_rsi(series: pd.Series, period: int = 14, smooth_k: int = 3, smooth_d: int = 3) -> Dict:
        """
        Расчет Stochastic RSI (NEW)
        Более чувствительный индикатор перекупленности/перепроданности
        """
        # Сначала рассчитываем RSI
        rsi = DataProcessor.calculate_rsi(series, period)

        # Stochastic применяем к RSI
        rsi_min = rsi.rolling(window=period).min()
        rsi_max = rsi.rolling(window=period).max()

        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min)

        # Сглаживание
        k = stoch_rsi.rolling(window=smooth_k).mean() * 100
        d = k.rolling(window=smooth_d).mean()

        return {'k': k, 'd': d}

    @staticmethod
    def calculate_macd(series: pd.Series, fast=12, slow=26, signal=9) -> Dict:
        """Расчет MACD"""
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            'macd': macd_line,
            'signal': signal_line,
            'histogram': histogram
        }

    @staticmethod
    def calculate_bollinger_bands(series: pd.Series, period=20, std_dev=2) -> Dict:
        """Расчет Bollinger Bands"""
        middle = series.rolling(window=period).mean()
        std = series.rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }

    @staticmethod
    def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Расчет ATR (Average True Range)"""
        high = df['high']
        low = df['low']
        close = df['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        return atr

    @staticmethod
    def calculate_obv(df: pd.DataFrame) -> pd.Series:
        """
        Расчет OBV - On Balance Volume (NEW)
        Показывает кумулятивное давление покупки/продажи
        Использует векторизованные операции для производительности
        """
        # Определяем направление цены
        price_direction = df['close'].diff()
        
        # Создаем множители: +1 для роста, -1 для падения, 0 для без изменений
        volume_multiplier = np.where(price_direction > 0, 1,
                                     np.where(price_direction < 0, -1, 0))
        
        # Умножаем объем на направление и считаем кумулятивную сумму
        obv = (df['volume'] * volume_multiplier).cumsum()
        
        # Устанавливаем первое значение равным объему
        obv.iloc[0] = df['volume'].iloc[0]
        
        return obv

    @staticmethod
    def calculate_vwap(df: pd.DataFrame) -> pd.Series:
        """
        Расчет VWAP - Volume Weighted Average Price (NEW)
        Средняя цена, взвешенная по объему
        """
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        return vwap

    @staticmethod
    def calculate_stochastic(df: pd.DataFrame, k_period=14, d_period=3) -> Dict:
        """Расчет Stochastic Oscillator"""
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()

        k = 100 * (df['close'] - low_min) / (high_max - low_min)
        d = k.rolling(window=d_period).mean()

        return {'k': k, 'd': d}

    @staticmethod
    def calculate_adx(df: pd.DataFrame, period: int = 14) -> Dict:
        """Расчет ADX - Average Directional Index"""
        high = df['high']
        low = df['low']
        close = df['close']

        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

        # Directional Movement
        up_move = high - high.shift()
        down_move = low.shift() - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        plus_dm = pd.Series(plus_dm, index=df.index)
        minus_dm = pd.Series(minus_dm, index=df.index)

        # Smoothed TR and DM
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)

        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()

        return {
            'adx': adx,
            'plus_di': plus_di,
            'minus_di': minus_di
        }

    def calculate_pivot_points(self, df: pd.DataFrame) -> Dict:
        """
        Расчет Pivot Points (NEW)
        Классические уровни поддержки и сопротивления
        """
        if len(df) < 1:
            return {}

        # Берем последнюю свечу
        last = df.iloc[-1]
        high = last['high']
        low = last['low']
        close = last['close']

        # Pivot Point
        pivot = (high + low + close) / 3

        # Поддержки
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)

        # Сопротивления
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)

        return {
            'pivot': pivot,
            'r1': r1,
            'r2': r2,
            'r3': r3,
            's1': s1,
            's2': s2,
            's3': s3
        }

    def determine_trend(self, df: pd.DataFrame) -> Dict:
        """
        Определение тренда (NEW улучшенная версия)
        
        Returns:
            Словарь с информацией о тренде
        """
        if df is None or len(df) < 50:
            return {'trend': 'unknown', 'strength': 0}

        try:
            last = df.iloc[-1]

            # Проверяем MA
            ma_trend = 'neutral'
            if pd.notna(last['ema_21']) and pd.notna(last['ema_55']):
                if last['close'] > last['ema_21'] > last['ema_55']:
                    ma_trend = 'uptrend'
                elif last['close'] < last['ema_21'] < last['ema_55']:
                    ma_trend = 'downtrend'

            # Проверяем ADX для силы тренда
            trend_strength = 0
            if 'adx' in df.columns and pd.notna(last['adx']):
                adx_value = last['adx']
                if adx_value > 50:
                    trend_strength = 3  # Very strong
                elif adx_value > 25:
                    trend_strength = 2  # Strong
                elif adx_value > 15:
                    trend_strength = 1  # Weak
                else:
                    trend_strength = 0  # No trend

            # Определяем направление по DI
            trend_direction = 'neutral'
            if 'plus_di' in df.columns and 'minus_di' in df.columns:
                if pd.notna(last['plus_di']) and pd.notna(last['minus_di']):
                    if last['plus_di'] > last['minus_di']:
                        trend_direction = 'bullish'
                    else:
                        trend_direction = 'bearish'

            # Комбинируем результаты
            if ma_trend == 'uptrend' and trend_direction == 'bullish':
                final_trend = 'strong_uptrend'
            elif ma_trend == 'uptrend':
                final_trend = 'uptrend'
            elif ma_trend == 'downtrend' and trend_direction == 'bearish':
                final_trend = 'strong_downtrend'
            elif ma_trend == 'downtrend':
                final_trend = 'downtrend'
            else:
                final_trend = 'sideways'

            return {
                'trend': final_trend,
                'strength': trend_strength,
                'ma_trend': ma_trend,
                'adx': last.get('adx', 0) if pd.notna(last.get('adx')) else 0
            }

        except Exception as e:
            logger.error(f"Ошибка определения тренда: {e}")
            return {'trend': 'unknown', 'strength': 0}

    async def get_market_overview(self, symbols: List[str], timeframe: str = '15m') -> Dict:
        """
        Получить обзор рынка (NEW)
        Анализ нескольких монет для общей картины
        
        Returns:
            Сводка по рынку
        """
        overview = {
            'total_symbols': len(symbols),
            'bullish_count': 0,
            'bearish_count': 0,
            'neutral_count': 0,
            'avg_rsi': 0,
            'high_volume_count': 0,
            'timestamp': datetime.utcnow().isoformat()
        }

        rsi_values = []
        
        for symbol in symbols[:20]:  # Ограничим для производительности
            try:
                df = await self.get_ohlcv(symbol, timeframe, limit=50)
                if df is None or len(df) < 20:
                    continue

                df = self.add_technical_indicators(df)
                last = df.iloc[-1]

                # Определяем тренд
                trend_info = self.determine_trend(df)
                
                if 'uptrend' in trend_info['trend']:
                    overview['bullish_count'] += 1
                elif 'downtrend' in trend_info['trend']:
                    overview['bearish_count'] += 1
                else:
                    overview['neutral_count'] += 1

                # RSI
                if pd.notna(last['rsi']):
                    rsi_values.append(last['rsi'])

                # Объем
                if last['volume_ratio'] > 2:
                    overview['high_volume_count'] += 1

            except Exception as e:
                logger.debug(f"Ошибка анализа {symbol}: {e}")
                continue

        # Средний RSI
        if rsi_values:
            overview['avg_rsi'] = round(sum(rsi_values) / len(rsi_values), 2)

        # Рыночное настроение
        total_directional = overview['bullish_count'] + overview['bearish_count']
        if total_directional > 0:
            bullish_pct = (overview['bullish_count'] / total_directional) * 100
            
            if bullish_pct > 70:
                overview['market_sentiment'] = 'bullish'
            elif bullish_pct < 30:
                overview['market_sentiment'] = 'bearish'
            else:
                overview['market_sentiment'] = 'mixed'
        else:
            overview['market_sentiment'] = 'neutral'

        return overview
