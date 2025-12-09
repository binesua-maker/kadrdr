import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from loguru import logger

class PatternRecognition:
    """Распознавание графических и свечных паттернов"""
    
    @staticmethod
    def find_triangles(df: pd.DataFrame, lookback: int = 50) -> List[Dict]:
        """Поиск треугольников (восходящий, нисходящий, симметричный)"""
        patterns = []
        
        if len(df) < lookback:
            return patterns
        
        recent = df.tail(lookback)
        
        # Находим максимумы и минимумы
        highs = recent['high'].rolling(window=5, center=True).max()
        lows = recent['low'].rolling(window=5, center=True).min()
        
        high_points = recent[recent['high'] == highs]['high']
        low_points = recent[recent['low'] == lows]['low']
        
        if len(high_points) >= 2 and len(low_points) >= 2:
            # Анализ наклона линий
            high_slope = np.polyfit(range(len(high_points)), high_points.values, 1)[0]
            low_slope = np.polyfit(range(len(low_points)), low_points.values, 1)[0]
            
            # Восходящий треугольник
            if abs(high_slope) < 0.001 and low_slope > 0:
                patterns.append({
                    'type': 'ascending_triangle',
                    'direction': 'bullish',
                    'resistance': high_points.mean(),
                    'support_slope': low_slope,
                    'reliability': 'high'
                })
            
            # Нисходящий треугольник
            elif abs(low_slope) < 0.001 and high_slope < 0:
                patterns.append({
                    'type': 'descending_triangle',
                    'direction': 'bearish',
                    'support': low_points.mean(),
                    'resistance_slope': high_slope,
                    'reliability': 'high'
                })
            
            # Симметричный треугольник
            elif high_slope < 0 and low_slope > 0:
                patterns.append({
                    'type': 'symmetrical_triangle',
                    'direction': 'neutral',
                    'apex_near': True if len(recent) > lookback * 0.8 else False,
                    'reliability': 'medium'
                })
        
        return patterns
    
    @staticmethod
    def find_head_and_shoulders(df: pd.DataFrame, lookback: int = 100) -> List[Dict]:
        """Поиск паттерна Голова и Плечи"""
        patterns = []
        
        if len(df) < lookback:
            return patterns
        
        recent = df.tail(lookback)
        
        # Находим три последовательных пика
        highs = recent['high'].rolling(window=7, center=True).max()
        peaks = recent[recent['high'] == highs]['high']
        
        if len(peaks) >= 3:
            peaks_list = peaks.tail(3).tolist()
            
            # Классическая голова и плечи
            if (peaks_list[1] > peaks_list[0] and 
                peaks_list[1] > peaks_list[2] and
                abs(peaks_list[0] - peaks_list[2]) / peaks_list[0] < 0.05):  # Плечи примерно равны
                
                patterns.append({
                    'type': 'head_and_shoulders',
                    'direction': 'bearish',
                    'left_shoulder': peaks_list[0],
                    'head': peaks_list[1],
                    'right_shoulder': peaks_list[2],
                    'neckline': recent['low'].tail(50).mean(),
                    'reliability': 'high'
                })
        
        # Перевернутая голова и плечи
        lows = recent['low'].rolling(window=7, center=True).min()
        valleys = recent[recent['low'] == lows]['low']
        
        if len(valleys) >= 3:
            valleys_list = valleys.tail(3).tolist()
            
            if (valleys_list[1] < valleys_list[0] and 
                valleys_list[1] < valleys_list[2] and
                abs(valleys_list[0] - valleys_list[2]) / valleys_list[0] < 0.05):
                
                patterns.append({
                    'type': 'inverse_head_and_shoulders',
                    'direction': 'bullish',
                    'left_shoulder': valleys_list[0],
                    'head': valleys_list[1],
                    'right_shoulder': valleys_list[2],
                    'neckline': recent['high'].tail(50).mean(),
                    'reliability': 'high'
                })
        
        return patterns
    
    @staticmethod
    def find_flags_and_pennants(df: pd.DataFrame) -> List[Dict]:
        """Поиск флагов и вымпелов"""
        patterns = []
        
        if len(df) < 30:
            return patterns
        
        # Ищем сильное движение (флагшток)
        price_change = (df['close'].iloc[-20] - df['close'].iloc[-30]) / df['close'].iloc[-30]
        
        if abs(price_change) > 0.05:  # Движение больше 5%
            # Анализируем последние 10 свечей на консолидацию
            consolidation = df.tail(10)
            volatility = consolidation['high'].max() - consolidation['low'].min()
            avg_volatility = (df['high'] - df['low']).tail(30).mean()
            
            if volatility < avg_volatility * 0.7:  # Снижение волатильности
                pattern_type = 'bull_flag' if price_change > 0 else 'bear_flag'
                
                patterns.append({
                    'type': pattern_type,
                    'direction': 'bullish' if price_change > 0 else 'bearish',
                    'flagpole_move': round(price_change * 100, 2),
                    'consolidation_range': round(volatility, 2),
                    'reliability': 'medium'
                })
        
        return patterns
    
    @staticmethod
    def find_double_top_bottom(df: pd.DataFrame, lookback: int = 50) -> List[Dict]:
        """Поиск двойных вершин и оснований"""
        patterns = []
        
        if len(df) < lookback:
            return patterns
        
        recent = df.tail(lookback)
        
        # Двойная вершина
        highs = recent['high'].rolling(window=5, center=True).max()
        peaks = recent[recent['high'] == highs]['high']
        
        if len(peaks) >= 2:
            last_two_peaks = peaks.tail(2).tolist()
            
            # Проверяем, что пики примерно на одном уровне
            if abs(last_two_peaks[0] - last_two_peaks[1]) / last_two_peaks[0] < 0.02:
                patterns.append({
                    'type': 'double_top',
                    'direction': 'bearish',
                    'level': (last_two_peaks[0] + last_two_peaks[1]) / 2,
                    'reliability': 'high'
                })
        
        # Двойное основание
        lows = recent['low'].rolling(window=5, center=True).min()
        valleys = recent[recent['low'] == lows]['low']
        
        if len(valleys) >= 2:
            last_two_valleys = valleys.tail(2).tolist()
            
            if abs(last_two_valleys[0] - last_two_valleys[1]) / last_two_valleys[0] < 0.02:
                patterns.append({
                    'type': 'double_bottom',
                    'direction': 'bullish',
                    'level': (last_two_valleys[0] + last_two_valleys[1]) / 2,
                    'reliability': 'high'
                })
        
        return patterns
    
    @staticmethod
    def detect_candlestick_patterns(df: pd.DataFrame) -> List[Dict]:
        """Распознавание свечных паттернов"""
        patterns = []
        
        if len(df) < 3:
            return patterns
        
        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        body = abs(last_candle['close'] - last_candle['open'])
        upper_shadow = last_candle['high'] - max(last_candle['close'], last_candle['open'])
        lower_shadow = min(last_candle['close'], last_candle['open']) - last_candle['low']
        candle_range = last_candle['high'] - last_candle['low']
        
        # Молот (Hammer)
        if (lower_shadow > body * 2 and 
            upper_shadow < body * 0.3 and
            last_candle['close'] > last_candle['open']):
            patterns.append({
                'type': 'hammer',
                'direction': 'bullish',
                'reliability': 'medium',
                'description': 'Молот - бычий разворотный паттерн'
            })
        
        # Падающая звезда (Shooting Star)
        if (upper_shadow > body * 2 and 
            lower_shadow < body * 0.3 and
            last_candle['close'] < last_candle['open']):
            patterns.append({
                'type': 'shooting_star',
                'direction': 'bearish',
                'reliability': 'medium',
                'description': 'Падающая звезда - медвежий разворотный паттерн'
            })
        
        # Доджи (Doji)
        if body < candle_range * 0.1:
            patterns.append({
                'type': 'doji',
                'direction': 'neutral',
                'reliability': 'low',
                'description': 'Доджи - неопределенность рынка'
            })
        
        # Бычье поглощение (Bullish Engulfing)
        prev_body = abs(prev_candle['close'] - prev_candle['open'])
        if (prev_candle['close'] < prev_candle['open'] and  # Предыдущая - медвежья
            last_candle['close'] > last_candle['open'] and   # Текущая - бычья
            last_candle['close'] > prev_candle['open'] and
            last_candle['open'] < prev_candle['close'] and
            body > prev_body):
            patterns.append({
                'type': 'bullish_engulfing',
                'direction': 'bullish',
                'reliability': 'high',
                'description': 'Бычье поглощение - сильный бычий сигнал'
            })
        
        # Медвежье поглощение (Bearish Engulfing)
        if (prev_candle['close'] > prev_candle['open'] and  # Предыдущая - бычья
            last_candle['close'] < last_candle['open'] and   # Текущая - медвежья
            last_candle['close'] < prev_candle['open'] and
            last_candle['open'] > prev_candle['close'] and
            body > prev_body):
            patterns.append({
                'type': 'bearish_engulfing',
                'direction': 'bearish',
                'reliability': 'high',
                'description': 'Медвежье поглощение - сильный медвежий сигнал'
            })
        
        return patterns