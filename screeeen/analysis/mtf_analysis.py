"""
Multi-Timeframe Analysis (MTF) - Мульти-таймфрейм анализ
"""
from typing import Dict, List, Optional
from loguru import logger
import pandas as pd
import numpy as np
from data.binance_client import BinanceDataClient
from data.data_processor import DataProcessor


class MTFAnalyzer:
    """Анализ на нескольких таймфреймах"""
    
    def __init__(self):
        self.binance = BinanceDataClient()
        self.processor = DataProcessor()
        self.timeframes = ['15m', '1h', '4h', '1d']
    
    async def analyze_symbol(self, symbol: str) -> Dict:
        """
        Провести мульти-таймфрейм анализ символа
        
        Args:
            symbol: Символ монеты (например, 'BTC/USDT')
        
        Returns:
            Словарь с результатами анализа по каждому таймфрейму
        """
        try:
            results = {
                'symbol': symbol,
                'timeframes': {},
                'alignment_score': 0,
                'recommendation': 'neutral',
                'confidence': 0
            }
            
            # Анализируем каждый таймфрейм
            for tf in self.timeframes:
                tf_analysis = await self._analyze_timeframe(symbol, tf)
                if tf_analysis:
                    results['timeframes'][tf] = tf_analysis
            
            # Если нет данных
            if not results['timeframes']:
                return results
            
            # Рассчитываем alignment score
            results['alignment_score'] = self._calculate_alignment_score(results['timeframes'])
            
            # Определяем рекомендацию
            results['recommendation'] = self._get_recommendation(results['timeframes'], results['alignment_score'])
            
            # Рассчитываем уверенность
            results['confidence'] = self._calculate_confidence(results['timeframes'], results['alignment_score'])
            
            return results
            
        except Exception as e:
            logger.error(f"Ошибка MTF анализа для {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e),
                'timeframes': {},
                'alignment_score': 0,
                'recommendation': 'neutral',
                'confidence': 0
            }
    
    async def _analyze_timeframe(self, symbol: str, timeframe: str) -> Optional[Dict]:
        """Анализ на одном таймфрейме"""
        try:
            # Получаем данные
            df = await self.binance.get_ohlcv(symbol, timeframe, limit=200)
            if df is None or len(df) < 50:
                return None
            
            # Добавляем индикаторы
            df = self.processor.add_technical_indicators(df)
            
            # Последние значения
            last = df.iloc[-1]
            prev = df.iloc[-2]
            
            # Определяем тренд
            trend = self._determine_trend(df)
            
            # RSI состояние
            rsi_state = self._get_rsi_state(last['rsi'])
            
            # MACD состояние
            macd_state = 'bullish' if last['macd'] > last['macd_signal'] else 'bearish'
            
            # Положение относительно MA
            ma_position = self._get_ma_position(last)
            
            # Momentum
            momentum = self._calculate_momentum(df)
            
            return {
                'trend': trend,
                'rsi': float(last['rsi']) if not pd.isna(last['rsi']) else None,
                'rsi_state': rsi_state,
                'macd_state': macd_state,
                'ma_position': ma_position,
                'momentum': momentum,
                'price': float(last['close']),
                'volume_trend': 'increasing' if last['volume'] > df['volume'].tail(20).mean() else 'decreasing'
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа таймфрейма {timeframe} для {symbol}: {e}")
            return None
    
    def _determine_trend(self, df: pd.DataFrame) -> str:
        """Определить тренд на основе MA"""
        try:
            last = df.iloc[-1]
            
            # Используем EMA для определения тренда
            if pd.isna(last['ema_21']) or pd.isna(last['ema_55']):
                return 'neutral'
            
            if last['close'] > last['ema_21'] > last['ema_55']:
                return 'uptrend'
            elif last['close'] < last['ema_21'] < last['ema_55']:
                return 'downtrend'
            else:
                return 'sideways'
                
        except Exception:
            return 'neutral'
    
    def _get_rsi_state(self, rsi: float) -> str:
        """Получить состояние RSI"""
        if pd.isna(rsi):
            return 'neutral'
        
        if rsi < 30:
            return 'oversold'
        elif rsi > 70:
            return 'overbought'
        elif rsi < 40:
            return 'weak'
        elif rsi > 60:
            return 'strong'
        else:
            return 'neutral'
    
    def _get_ma_position(self, candle: pd.Series) -> str:
        """Определить положение относительно скользящих средних"""
        try:
            if pd.isna(candle['sma_20']) or pd.isna(candle['sma_50']):
                return 'neutral'
            
            price = candle['close']
            
            if price > candle['sma_20'] > candle['sma_50']:
                return 'above_all'
            elif price < candle['sma_20'] < candle['sma_50']:
                return 'below_all'
            else:
                return 'mixed'
                
        except Exception:
            return 'neutral'
    
    def _calculate_momentum(self, df: pd.DataFrame) -> str:
        """Рассчитать momentum"""
        try:
            # Сравниваем текущую цену с ценой 10 свечей назад
            current_price = df.iloc[-1]['close']
            past_price = df.iloc[-10]['close']
            
            change = ((current_price - past_price) / past_price) * 100
            
            if change > 2:
                return 'strong_bullish'
            elif change > 0.5:
                return 'bullish'
            elif change < -2:
                return 'strong_bearish'
            elif change < -0.5:
                return 'bearish'
            else:
                return 'neutral'
                
        except Exception:
            return 'neutral'
    
    def _calculate_alignment_score(self, timeframes: Dict) -> float:
        """
        Рассчитать alignment score (согласованность трендов)
        Возвращает значение от 0 до 100
        """
        if not timeframes:
            return 0
        
        # Подсчитываем направления трендов
        trends = [tf.get('trend', 'neutral') for tf in timeframes.values()]
        
        uptrend_count = trends.count('uptrend')
        downtrend_count = trends.count('downtrend')
        
        total = len(trends)
        
        # Максимальная согласованность в одном направлении
        max_alignment = max(uptrend_count, downtrend_count)
        
        score = (max_alignment / total) * 100
        
        return round(score, 2)
    
    def _get_recommendation(self, timeframes: Dict, alignment_score: float) -> str:
        """Получить рекомендацию на основе анализа"""
        if not timeframes:
            return 'neutral'
        
        # Подсчитываем бычьи и медвежьи сигналы
        bullish_signals = 0
        bearish_signals = 0
        
        for tf_data in timeframes.values():
            if tf_data.get('trend') == 'uptrend':
                bullish_signals += 2
            elif tf_data.get('trend') == 'downtrend':
                bearish_signals += 2
            
            if tf_data.get('macd_state') == 'bullish':
                bullish_signals += 1
            elif tf_data.get('macd_state') == 'bearish':
                bearish_signals += 1
            
            if tf_data.get('momentum') in ['bullish', 'strong_bullish']:
                bullish_signals += 1
            elif tf_data.get('momentum') in ['bearish', 'strong_bearish']:
                bearish_signals += 1
        
        # Определяем рекомендацию
        if bullish_signals > bearish_signals * 1.5 and alignment_score > 60:
            return 'strong_buy'
        elif bullish_signals > bearish_signals:
            return 'buy'
        elif bearish_signals > bullish_signals * 1.5 and alignment_score > 60:
            return 'strong_sell'
        elif bearish_signals > bullish_signals:
            return 'sell'
        else:
            return 'neutral'
    
    def _calculate_confidence(self, timeframes: Dict, alignment_score: float) -> float:
        """Рассчитать уверенность в рекомендации (0-100)"""
        if not timeframes:
            return 0
        
        # Базовая уверенность от alignment score
        confidence = alignment_score * 0.6
        
        # Бонус за количество таймфреймов
        tf_count = len(timeframes)
        confidence += (tf_count / len(self.timeframes)) * 20
        
        # Бонус за сильные momentum сигналы
        strong_momentum_count = sum(
            1 for tf in timeframes.values()
            if tf.get('momentum') in ['strong_bullish', 'strong_bearish']
        )
        confidence += (strong_momentum_count / tf_count) * 20 if tf_count > 0 else 0
        
        return min(round(confidence, 2), 100)
    
    def format_analysis(self, analysis: Dict) -> str:
        """Форматировать результаты анализа для отображения"""
        symbol = analysis.get('symbol', 'N/A')
        
        text = f"📊 <b>Мульти-таймфрейм анализ: {symbol}</b>\n\n"
        
        # Таймфреймы
        timeframes = analysis.get('timeframes', {})
        for tf, data in timeframes.items():
            trend_emoji = {
                'uptrend': '📈',
                'downtrend': '📉',
                'sideways': '↔️',
                'neutral': '➖'
            }.get(data.get('trend', 'neutral'), '➖')
            
            text += f"<b>{tf}:</b> {trend_emoji} {data.get('trend', 'N/A').upper()}\n"
            text += f"  RSI: {data.get('rsi', 'N/A'):.1f} ({data.get('rsi_state', 'N/A')})\n"
            text += f"  MACD: {data.get('macd_state', 'N/A')}\n"
            text += f"  Momentum: {data.get('momentum', 'N/A')}\n\n"
        
        # Общая оценка
        alignment = analysis.get('alignment_score', 0)
        text += f"🎯 <b>Согласованность:</b> {alignment:.1f}%\n"
        
        recommendation = analysis.get('recommendation', 'neutral')
        rec_emoji = {
            'strong_buy': '🟢',
            'buy': '🟩',
            'neutral': '⚪',
            'sell': '🟥',
            'strong_sell': '🔴'
        }.get(recommendation, '⚪')
        
        text += f"{rec_emoji} <b>Рекомендация:</b> {recommendation.upper()}\n"
        text += f"💪 <b>Уверенность:</b> {analysis.get('confidence', 0):.1f}%\n"
        
        return text
