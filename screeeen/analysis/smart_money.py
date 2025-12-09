import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from loguru import logger
from config.settings import (
    FVG_MIN_SIZE,
    ORDER_BLOCK_LOOKBACK,
    LIQUIDITY_THRESHOLD
)

class SmartMoneyAnalysis:
    """Анализ на основе Smart Money Concepts"""
    
    @staticmethod
    def find_order_blocks(df: pd.DataFrame, lookback: int = ORDER_BLOCK_LOOKBACK) -> List[Dict]:
        """
        Поиск Order Blocks (зон интереса крупных игроков)
        Order Block - последняя свеча перед сильным импульсом
        """
        order_blocks = []
        
        for i in range(lookback, len(df) - 1):
            current = df.iloc[i]
            next_candle = df.iloc[i + 1]
            prev_candles = df.iloc[i - lookback:i]
            
            # Бычий Order Block (перед резким ростом)
            if next_candle['close'] > next_candle['open']:
                move_size = (next_candle['high'] - next_candle['low']) / next_candle['low'] * 100
                
                if move_size > 2:  # Движение больше 2%
                    order_blocks.append({
                        'type': 'bullish',
                        'timestamp': df.index[i],
                        'price_low': current['low'],
                        'price_high': current['high'],
                        'strength': move_size
                    })
            
            # Медвежий Order Block (перед резким падением)
            elif next_candle['close'] < next_candle['open']:
                move_size = (next_candle['high'] - next_candle['low']) / next_candle['high'] * 100
                
                if move_size > 2:
                    order_blocks.append({
                        'type': 'bearish',
                        'timestamp': df.index[i],
                        'price_low': current['low'],
                        'price_high': current['high'],
                        'strength': move_size
                    })
        
        return order_blocks
    
    @staticmethod
    def find_fair_value_gaps(df: pd.DataFrame, min_gap_size: float = FVG_MIN_SIZE) -> List[Dict]:
        """
        Поиск Fair Value Gaps (FVG) - имбалансы/гэпы в цене
        FVG = зона, где цена двигалась слишком быстро, оставив неэффективность
        """
        fvgs = []
        
        for i in range(2, len(df)):
            candle_1 = df.iloc[i - 2]
            candle_2 = df.iloc[i - 1]
            candle_3 = df.iloc[i]
            
            # Бычий FVG (гэп вверх)
            if candle_1['high'] < candle_3['low']:
                gap_size = (candle_3['low'] - candle_1['high']) / candle_1['high'] * 100
                
                if gap_size >= min_gap_size:
                    fvgs.append({
                        'type': 'bullish',
                        'timestamp': df.index[i],
                        'gap_low': candle_1['high'],
                        'gap_high': candle_3['low'],
                        'size': gap_size,
                        'filled': False
                    })
            
            # Медвежий FVG (гэп вниз)
            elif candle_1['low'] > candle_3['high']:
                gap_size = (candle_1['low'] - candle_3['high']) / candle_3['high'] * 100
                
                if gap_size >= min_gap_size:
                    fvgs.append({
                        'type': 'bearish',
                        'timestamp': df.index[i],
                        'gap_low': candle_3['high'],
                        'gap_high': candle_1['low'],
                        'size': gap_size,
                        'filled': False
                    })
        
        return fvgs
    
    @staticmethod
    def detect_break_of_structure(df: pd.DataFrame, swing_period: int = 5) -> List[Dict]:
        """
        Определение Break of Structure (BOS) - слом структуры тренда
        """
        bos_signals = []
        
        # Находим свинг хаи и лои
        df['swing_high'] = df['high'].rolling(window=swing_period * 2 + 1, center=True).max()
        df['swing_low'] = df['low'].rolling(window=swing_period * 2 + 1, center=True).min()
        
        df['is_swing_high'] = df['high'] == df['swing_high']
        df['is_swing_low'] = df['low'] == df['swing_low']
        
        swing_highs = df[df['is_swing_high']]['high'].tolist()
        swing_lows = df[df['is_swing_low']]['low'].tolist()
        
        # Определяем бычий BOS (пробой предыдущего хая)
        for i in range(1, len(swing_highs)):
            if swing_highs[i] > swing_highs[i - 1]:
                bos_signals.append({
                    'type': 'bullish_bos',
                    'timestamp': df.index[-1],
                    'previous_high': swing_highs[i - 1],
                    'new_high': swing_highs[i],
                    'strength': (swing_highs[i] - swing_highs[i - 1]) / swing_highs[i - 1] * 100
                })
        
        # Определяем медвежий BOS (пробой предыдущего лоу)
        for i in range(1, len(swing_lows)):
            if swing_lows[i] < swing_lows[i - 1]:
                bos_signals.append({
                    'type': 'bearish_bos',
                    'timestamp': df.index[-1],
                    'previous_low': swing_lows[i - 1],
                    'new_low': swing_lows[i],
                    'strength': (swing_lows[i - 1] - swing_lows[i]) / swing_lows[i - 1] * 100
                })
        
        return bos_signals
    
    @staticmethod
    def find_liquidity_zones(df: pd.DataFrame, orderbook: Optional[Dict] = None) -> List[Dict]:
        """
        Поиск зон ликвидности (где скапливаются стопы)
        """
        liquidity_zones = []
        
        # Находим локальные максимумы/минимумы (равные хаи/лои)
        df['prev_high'] = df['high'].shift(1)
        df['next_high'] = df['high'].shift(-1)
        df['prev_low'] = df['low'].shift(1)
        df['next_low'] = df['low'].shift(-1)
        
        # Равные хаи (зона ликвидности сверху)
        equal_highs = df[
            (abs(df['high'] - df['prev_high']) / df['high'] < 0.002) |
            (abs(df['high'] - df['next_high']) / df['high'] < 0.002)
        ]
        
        for idx in equal_highs.index:
            liquidity_zones.append({
                'type': 'resistance_liquidity',
                'timestamp': idx,
                'price': equal_highs.loc[idx, 'high'],
                'touches': 2
            })
        
        # Равные лои (зона ликвидности снизу)
        equal_lows = df[
            (abs(df['low'] - df['prev_low']) / df['low'] < 0.002) |
            (abs(df['low'] - df['next_low']) / df['low'] < 0.002)
        ]
        
        for idx in equal_lows.index:
            liquidity_zones.append({
                'type': 'support_liquidity',
                'timestamp': idx,
                'price': equal_lows.loc[idx, 'low'],
                'touches': 2
            })
        
        return liquidity_zones
    
    @staticmethod
    def detect_liquidity_sweep(df: pd.DataFrame, liquidity_zones: List[Dict]) -> List[Dict]:
        """
        Определение Liquidity Sweep (сбор ликвидности перед разворотом)
        """
        sweeps = []
        current_price = df['close'].iloc[-1]
        
        for zone in liquidity_zones:
            zone_price = zone['price']
            
            # Проверяем, была ли ликвидация
            if zone['type'] == 'resistance_liquidity':
                # Цена пробила уровень и вернулась
                high_breach = df['high'].max()
                if high_breach > zone_price and current_price < zone_price:
                    sweeps.append({
                        'type': 'bearish_sweep',
                        'timestamp': df.index[-1],
                        'liquidity_level': zone_price,
                        'sweep_high': high_breach,
                        'current_price': current_price
                    })
            
            elif zone['type'] == 'support_liquidity':
                low_breach = df['low'].min()
                if low_breach < zone_price and current_price > zone_price:
                    sweeps.append({
                        'type': 'bullish_sweep',
                        'timestamp': df.index[-1],
                        'liquidity_level': zone_price,
                        'sweep_low': low_breach,
                        'current_price': current_price
                    })
        
        return sweeps