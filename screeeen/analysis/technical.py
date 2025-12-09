import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger
from config.settings import RSI_OVERSOLD, RSI_OVERBOUGHT

class TechnicalAnalysis:
    """Технический анализ криптовалют"""
    
    @staticmethod
    def detect_trend(df: pd.DataFrame) -> Dict:
        """Определение тренда"""
        if len(df) < 50:
            return {'trend': 'unknown', 'strength': 0}
        
        current_price = df['close'].iloc[-1]
        sma_20 = df['sma_20'].iloc[-1] if 'sma_20' in df else None
        sma_50 = df['sma_50'].iloc[-1] if 'sma_50' in df else None
        ema_9 = df['ema_9'].iloc[-1] if 'ema_9' in df else None
        ema_21 = df['ema_21'].iloc[-1] if 'ema_21' in df else None
        
        bullish_signals = 0
        bearish_signals = 0
        
        # Проверка положения цены относительно MA
        if sma_20 and current_price > sma_20:
            bullish_signals += 1
        elif sma_20 and current_price < sma_20:
            bearish_signals += 1
        
        if sma_50 and current_price > sma_50:
            bullish_signals += 1
        elif sma_50 and current_price < sma_50:
            bearish_signals += 1
        
        # EMA crossover
        if ema_9 and ema_21:
            if ema_9 > ema_21:
                bullish_signals += 2
            else:
                bearish_signals += 2
        
        # Определение тренда
        total_signals = bullish_signals + bearish_signals
        if total_signals == 0:
            return {'trend': 'sideways', 'strength': 0}
        
        strength = abs(bullish_signals - bearish_signals) / total_signals * 100
        
        if bullish_signals > bearish_signals:
            return {'trend': 'bullish', 'strength': round(strength, 2)}
        elif bearish_signals > bullish_signals:
            return {'trend': 'bearish', 'strength': round(strength, 2)}
        else:
            return {'trend': 'sideways', 'strength': 0}
    
    @staticmethod
    def find_rsi_divergence(df: pd.DataFrame, lookback: int = 50) -> List[Dict]:
        """Поиск дивергенций RSI"""
        divergences = []
        
        if 'rsi' not in df or len(df) < lookback:
            return divergences
        
        recent_df = df.tail(lookback)
        
        # Находим локальные максимумы и минимумы цены и RSI
        price_highs = recent_df['high'].rolling(window=5, center=True).max()
        price_lows = recent_df['low'].rolling(window=5, center=True).min()
        rsi_highs = recent_df['rsi'].rolling(window=5, center=True).max()
        rsi_lows = recent_df['rsi'].rolling(window=5, center=True).min()
        
        price_high_points = recent_df[recent_df['high'] == price_highs]
        price_low_points = recent_df[recent_df['low'] == price_lows]
        
        # Бычья дивергенция (цена падает, RSI растет)
        if len(price_low_points) >= 2:
            last_two_lows = price_low_points.tail(2)
            if len(last_two_lows) == 2:
                idx1, idx2 = last_two_lows.index[0], last_two_lows.index[1]
                
                if (last_two_lows.iloc[1]['low'] < last_two_lows.iloc[0]['low'] and
                    df.loc[idx2, 'rsi'] > df.loc[idx1, 'rsi']):
                    divergences.append({
                        'type': 'bullish',
                        'price_point1': last_two_lows.iloc[0]['low'],
                        'price_point2': last_two_lows.iloc[1]['low'],
                        'rsi_point1': df.loc[idx1, 'rsi'],
                        'rsi_point2': df.loc[idx2, 'rsi'],
                        'timestamp': df.index[-1]
                    })
        
        # Медвежья дивергенция (цена растет, RSI падает)
        if len(price_high_points) >= 2:
            last_two_highs = price_high_points.tail(2)
            if len(last_two_highs) == 2:
                idx1, idx2 = last_two_highs.index[0], last_two_highs.index[1]
                
                if (last_two_highs.iloc[1]['high'] > last_two_highs.iloc[0]['high'] and
                    df.loc[idx2, 'rsi'] < df.loc[idx1, 'rsi']):
                    divergences.append({
                        'type': 'bearish',
                        'price_point1': last_two_highs.iloc[0]['high'],
                        'price_point2': last_two_highs.iloc[1]['high'],
                        'rsi_point1': df.loc[idx1, 'rsi'],
                        'rsi_point2': df.loc[idx2, 'rsi'],
                        'timestamp': df.index[-1]
                    })
        
        return divergences
    
    @staticmethod
    def find_macd_divergence(df: pd.DataFrame, lookback: int = 50) -> List[Dict]:
        """Поиск дивергенций MACD"""
        divergences = []
        
        if 'macd' not in df or len(df) < lookback:
            return divergences
        
        recent_df = df.tail(lookback)
        
        # Находим локальные экстремумы
        price_highs = recent_df['high'].rolling(window=5, center=True).max()
        price_lows = recent_df['low'].rolling(window=5, center=True).min()
        
        price_high_points = recent_df[recent_df['high'] == price_highs]
        price_low_points = recent_df[recent_df['low'] == price_lows]
        
        # Бычья дивергенция MACD
        if len(price_low_points) >= 2:
            last_two_lows = price_low_points.tail(2)
            if len(last_two_lows) == 2:
                idx1, idx2 = last_two_lows.index[0], last_two_lows.index[1]
                
                if (last_two_lows.iloc[1]['low'] < last_two_lows.iloc[0]['low'] and
                    df.loc[idx2, 'macd'] > df.loc[idx1, 'macd']):
                    divergences.append({
                        'type': 'bullish',
                        'indicator': 'MACD',
                        'timestamp': df.index[-1]
                    })
        
        # Медвежья дивергенция MACD
        if len(price_high_points) >= 2:
            last_two_highs = price_high_points.tail(2)
            if len(last_two_highs) == 2:
                idx1, idx2 = last_two_highs.index[0], last_two_highs.index[1]
                
                if (last_two_highs.iloc[1]['high'] > last_two_highs.iloc[0]['high'] and
                    df.loc[idx2, 'macd'] < df.loc[idx1, 'macd']):
                    divergences.append({
                        'type': 'bearish',
                        'indicator': 'MACD',
                        'timestamp': df.index[-1]
                    })
        
        return divergences
    
    @staticmethod
    def check_rsi_conditions(df: pd.DataFrame) -> Optional[Dict]:
        """Проверка условий RSI"""
        if 'rsi' not in df or len(df) < 2:
            return None
        
        current_rsi = df['rsi'].iloc[-1]
        prev_rsi = df['rsi'].iloc[-2]
        
        signal = None
        
        if current_rsi < RSI_OVERSOLD and prev_rsi >= RSI_OVERSOLD:
            signal = {
                'type': 'oversold',
                'rsi': round(current_rsi, 2),
                'message': 'RSI вошел в зону перепроданности'
            }
        elif current_rsi > RSI_OVERBOUGHT and prev_rsi <= RSI_OVERBOUGHT:
            signal = {
                'type': 'overbought',
                'rsi': round(current_rsi, 2),
                'message': 'RSI вошел в зону перекупленности'
            }
        
        return signal
    
    @staticmethod
    def check_macd_crossover(df: pd.DataFrame) -> Optional[Dict]:
        """Проверка пересечения MACD"""
        if 'macd' not in df or 'macd_signal' not in df or len(df) < 2:
            return None
        
        macd_curr = df['macd'].iloc[-1]
        signal_curr = df['macd_signal'].iloc[-1]
        macd_prev = df['macd'].iloc[-2]
        signal_prev = df['macd_signal'].iloc[-2]
        
        # Бычье пересечение
        if macd_prev <= signal_prev and macd_curr > signal_curr:
            return {
                'type': 'bullish_crossover',
                'macd': round(macd_curr, 4),
                'signal': round(signal_curr, 4),
                'message': 'MACD пересек сигнальную линию снизу вверх'
            }
        
        # Медвежье пересечение
        elif macd_prev >= signal_prev and macd_curr < signal_curr:
            return {
                'type': 'bearish_crossover',
                'macd': round(macd_curr, 4),
                'signal': round(signal_curr, 4),
                'message': 'MACD пересек сигнальную линию сверху вниз'
            }
        
        return None
    
    @staticmethod
    def check_bollinger_squeeze(df: pd.DataFrame) -> Optional[Dict]:
        """Проверка сжатия Bollinger Bands (волатильность)"""
        if 'bb_upper' not in df or 'bb_lower' not in df or len(df) < 20:
            return None
        
        current_width = (df['bb_upper'].iloc[-1] - df['bb_lower'].iloc[-1]) / df['bb_middle'].iloc[-1]
        avg_width = ((df['bb_upper'] - df['bb_lower']) / df['bb_middle']).tail(20).mean()
        
        if current_width < avg_width * 0.5:  # Сжатие более чем на 50%
            return {
                'type': 'squeeze',
                'width': round(current_width * 100, 2),
                'avg_width': round(avg_width * 100, 2),
                'message': 'Bollinger Bands сжимаются - ожидается сильное движение'
            }
        
        return None
    
    @staticmethod
    def calculate_strength_index(df: pd.DataFrame) -> float:
        """Расчет индекса силы тренда (0-100)"""
        score = 0
        max_score = 10
        
        if len(df) < 50:
            return 0
        
        current_price = df['close'].iloc[-1]
        
        # 1. Положение относительно MA (3 балла)
        if 'sma_20' in df and current_price > df['sma_20'].iloc[-1]:
            score += 1
        if 'sma_50' in df and current_price > df['sma_50'].iloc[-1]:
            score += 1
        if 'ema_21' in df and current_price > df['ema_21'].iloc[-1]:
            score += 1
        
        # 2. RSI (2 балла)
        if 'rsi' in df:
            rsi = df['rsi'].iloc[-1]
            if 40 < rsi < 70:  # Здоровый тренд
                score += 2
            elif 30 < rsi < 80:
                score += 1
        
        # 3. MACD (2 балла)
        if 'macd' in df and 'macd_signal' in df:
            if df['macd'].iloc[-1] > df['macd_signal'].iloc[-1]:
                score += 2
        
        # 4. Объем (2 балла)
        if 'volume_ratio' in df and df['volume_ratio'].iloc[-1] > 1:
            score += 2
        
        # 5. Волатильность (1 балл)
        if 'atr' in df and df['atr'].iloc[-1] > df['atr'].mean():
            score += 1
        
        return round((score / max_score) * 100, 2)