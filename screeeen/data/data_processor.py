import pandas as pd
import numpy as np
from typing import Optional, Dict, List
from loguru import logger
import asyncio
from datetime import datetime, timedelta


class DataProcessor:
    """Обработка и нормализация данных с Binance"""

    def __init__(self):
        self.cache = {}
        self.cache_timeout = 60  # секунды

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Добавить технические индикаторы к DataFrame"""
        if df is None or len(df) < 20:
            return df

        try:
            # Simple Moving Averages
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_200'] = df['close'].rolling(window=200).mean()

            # Exponential Moving Averages
            df['ema_9'] = df['close'].ewm(span=9, adjust=False).mean()
            df['ema_21'] = df['close'].ewm(span=21, adjust=False).mean()
            df['ema_55'] = df['close'].ewm(span=55, adjust=False).mean()

            # RSI
            df['rsi'] = self.calculate_rsi(df['close'], period=14)

            # MACD
            macd_data = self.calculate_macd(df['close'])
            df['macd'] = macd_data['macd']
            df['macd_signal'] = macd_data['signal']
            df['macd_histogram'] = macd_data['histogram']

            # Bollinger Bands
            bb_data = self.calculate_bollinger_bands(df['close'])
            df['bb_upper'] = bb_data['upper']
            df['bb_middle'] = bb_data['middle']
            df['bb_lower'] = bb_data['lower']

            # ATR (Average True Range)
            df['atr'] = self.calculate_atr(df)

            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']

            # Stochastic
            stoch_data = self.calculate_stochastic(df)
            df['stoch_k'] = stoch_data['k']
            df['stoch_d'] = stoch_data['d']

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
    def calculate_stochastic(df: pd.DataFrame, k_period=14, d_period=3) -> Dict:
        """Расчет Stochastic Oscillator"""
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()

        k = 100 * (df['close'] - low_min) / (high_max - low_min)
        d = k.rolling(window=d_period).mean()

        return {'k': k, 'd': d}

    def find_support_resistance(self, df: pd.DataFrame, num_levels: int = 5) -> Dict[str, List[float]]:
        """Поиск уровней поддержки и сопротивления"""
        levels = {'support': [], 'resistance': []}

        try:
            # Находим локальные минимумы и максимумы
            window = 10
            df['local_min'] = df['low'].rolling(window=window * 2 + 1, center=True).min()
            df['local_max'] = df['high'].rolling(window=window * 2 + 1, center=True).max()

            # Уровни поддержки
            support_levels = df[df['low'] == df['local_min']]['low'].values
            support_levels = np.unique(np.round(support_levels, 2))

            # Уровни сопротивления
            resistance_levels = df[df['high'] == df['local_max']]['high'].values
            resistance_levels = np.unique(np.round(resistance_levels, 2))

            # Группируем близкие уровни
            support_levels = self._cluster_levels(support_levels, num_levels)
            resistance_levels = self._cluster_levels(resistance_levels, num_levels)

            levels['support'] = sorted(support_levels)[:num_levels]
            levels['resistance'] = sorted(resistance_levels, reverse=True)[:num_levels]

        except Exception as e:
            logger.error(f"Ошибка поиска уровней: {e}")

        return levels

    @staticmethod
    def _cluster_levels(levels: np.ndarray, num_clusters: int) -> List[float]:
        """Кластеризация близких уровней"""
        if len(levels) == 0:
            return []

        # Фильтруем нулевые и отрицательные значения
        levels = levels[levels > 0]

        if len(levels) == 0:
            return []

        # Простая кластеризация по близости
        sorted_levels = np.sort(levels)
        clusters = []
        current_cluster = [sorted_levels[0]]

        for level in sorted_levels[1:]:
            try:
                # Проверяем на валидность значений
                if level <= 0 or current_cluster[-1] <= 0:
                    current_cluster = [level]
                    continue

                # Вычисляем относительную разницу
                relative_diff = abs(level - current_cluster[-1]) / abs(current_cluster[-1])

                if relative_diff < 0.01:  # 1% разница
                    current_cluster.append(level)
                else:
                    # Сохраняем среднее значение кластера
                    cluster_mean = np.mean(current_cluster)
                    if cluster_mean > 0:  # Проверяем что среднее валидно
                        clusters.append(cluster_mean)
                    current_cluster = [level]
            except (ZeroDivisionError, ValueError, RuntimeWarning) as e:
                logger.debug(f"Пропускаем невалидный уровень: {level}")
                current_cluster = [level]
                continue

        # Добавляем последний кластер
        if current_cluster:
            cluster_mean = np.mean(current_cluster)
            if cluster_mean > 0:
                clusters.append(cluster_mean)

        # Возвращаем только валидные уровни
        valid_clusters = [c for c in clusters if c > 0 and not np.isnan(c) and not np.isinf(c)]

        return valid_clusters[:num_clusters]

    def calculate_price_change(self, df: pd.DataFrame, periods: List[int] = [1, 24, 168]) -> Dict:
        """Расчет изменения цены за разные периоды"""
        changes = {}

        if df is None or len(df) == 0:
            return changes

        current_price = df['close'].iloc[-1]

        for period in periods:
            if len(df) > period:
                old_price = df['close'].iloc[-period]
                if old_price > 0:  # Проверка деления на ноль
                    change = ((current_price - old_price) / old_price) * 100
                    changes[f'{period}h'] = round(change, 2)

        return changes

    def detect_volume_anomaly(self, df: pd.DataFrame, threshold: float = 2.0) -> Optional[Dict]:
        """Определение аномальных объемов"""
        if len(df) < 20:
            return None

        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].iloc[-20:-1].mean()

        # Проверка на валидность
        if avg_volume == 0 or pd.isna(avg_volume) or pd.isna(current_volume):
            return None

        if current_volume > avg_volume * threshold:
            return {
                'current_volume': float(current_volume),
                'average_volume': float(avg_volume),
                'ratio': float(current_volume / avg_volume),
                'is_anomaly': True
            }

        return None

    async def get_cached_data(self, key: str) -> Optional[any]:
        """Получить данные из кэша"""
        if key in self.cache:
            data, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.cache_timeout):
                return data
            else:
                del self.cache[key]
        return None

    async def set_cached_data(self, key: str, data: any):
        """Сохранить данные в кэш"""
        self.cache[key] = (data, datetime.now())

    def normalize_timeframe(self, tf: str) -> str:
        """Нормализация таймфрейма к формату CCXT"""
        mapping = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '1h', '4h': '4h', '1d': '1d', '1w': '1w'
        }
        return mapping.get(tf.lower(), '15m')

    def clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Очистка DataFrame от невалидных значений"""
        if df is None or len(df) == 0:
            return df

        try:
            # Заменяем inf на NaN
            df = df.replace([np.inf, -np.inf], np.nan)

            # Удаляем строки с NaN в критичных колонках
            critical_cols = ['open', 'high', 'low', 'close', 'volume']
            df = df.dropna(subset=critical_cols)

            # Убираем отрицательные значения цен
            for col in critical_cols:
                if col in df.columns:
                    df = df[df[col] > 0]

            return df

        except Exception as e:
            logger.error(f"Ошибка очистки DataFrame: {e}")
            return df

    def validate_data(self, df: pd.DataFrame) -> bool:
        """Валидация данных"""
        if df is None or len(df) == 0:
            return False

        required_cols = ['open', 'high', 'low', 'close', 'volume']

        # Проверяем наличие всех колонок
        if not all(col in df.columns for col in required_cols):
            return False

        # Проверяем на NaN
        if df[required_cols].isnull().any().any():
            return False

        # Проверяем на положительные значения
        if (df[required_cols] <= 0).any().any():
            return False

        return True