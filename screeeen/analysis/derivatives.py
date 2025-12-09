"""
Derivatives Analysis - Funding Rate & Open Interest
"""
from typing import Dict, List, Optional
from loguru import logger
import pandas as pd
from datetime import datetime, timedelta


class DerivativesAnalyzer:
    """Анализ деривативов: Funding Rate и Open Interest"""
    
    def __init__(self):
        self.exchange = None
        self._init_exchange()
    
    def _init_exchange(self):
        """Ленивая инициализация биржи"""
        try:
            import ccxt
            self.exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
        except Exception as e:
            logger.error(f"Ошибка инициализации биржи для деривативов: {e}")
    
    async def get_funding_rate(self, symbol: str) -> Dict:
        """
        Получить текущий Funding Rate для символа
        
        Args:
            symbol: Символ монеты (например, 'BTC/USDT')
        
        Returns:
            Информация о funding rate
        """
        try:
            if not self.exchange:
                self._init_exchange()
            
            # Получаем funding rate
            funding_rate = await self._fetch_funding_rate(symbol)
            
            if not funding_rate:
                return {'error': 'Не удалось получить funding rate'}
            
            # Анализируем sentiment
            sentiment = self._analyze_funding_sentiment(funding_rate)
            
            # Годовая ставка
            annualized_rate = funding_rate * 3 * 365  # 3 раза в день * 365 дней
            
            return {
                'symbol': symbol,
                'funding_rate': round(funding_rate * 100, 4),  # в процентах
                'annualized_rate': round(annualized_rate * 100, 2),
                'sentiment': sentiment,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения funding rate для {symbol}: {e}")
            return {'error': str(e)}
    
    async def _fetch_funding_rate(self, symbol: str) -> Optional[float]:
        """Получить funding rate с биржи"""
        try:
            # Пытаемся получить через API
            if self.exchange and hasattr(self.exchange, 'fetch_funding_rate'):
                result = self.exchange.fetch_funding_rate(symbol)
                return float(result.get('fundingRate', 0))
            
            # Альтернативный способ через funding history
            if self.exchange and hasattr(self.exchange, 'fetch_funding_rate_history'):
                history = self.exchange.fetch_funding_rate_history(symbol, limit=1)
                if history and len(history) > 0:
                    return float(history[0].get('fundingRate', 0))
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения funding rate: {e}")
            return None
    
    def _analyze_funding_sentiment(self, funding_rate: float) -> str:
        """
        Анализировать sentiment на основе funding rate
        
        Положительный FR = long positions платят short (bullish sentiment)
        Отрицательный FR = short positions платят long (bearish sentiment)
        """
        if funding_rate > 0.01:  # > 1%
            return 'extremely_bullish'
        elif funding_rate > 0.001:  # > 0.1%
            return 'bullish'
        elif funding_rate > -0.001:  # от -0.1% до 0.1%
            return 'neutral'
        elif funding_rate > -0.01:  # от -1% до -0.1%
            return 'bearish'
        else:
            return 'extremely_bearish'
    
    async def get_open_interest(self, symbol: str) -> Dict:
        """
        Получить Open Interest для символа
        
        Args:
            symbol: Символ монеты
        
        Returns:
            Информация об open interest
        """
        try:
            if not self.exchange:
                self._init_exchange()
            
            # Получаем Open Interest
            oi_data = await self._fetch_open_interest(symbol)
            
            if not oi_data:
                return {'error': 'Не удалось получить open interest'}
            
            # Получаем исторические данные для сравнения
            oi_history = await self._fetch_oi_history(symbol)
            
            # Анализ тренда OI
            oi_trend = self._analyze_oi_trend(oi_data, oi_history)
            
            return {
                'symbol': symbol,
                'open_interest': oi_data,
                'oi_trend': oi_trend,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения OI для {symbol}: {e}")
            return {'error': str(e)}
    
    async def _fetch_open_interest(self, symbol: str) -> Optional[float]:
        """Получить текущий Open Interest"""
        try:
            if self.exchange and hasattr(self.exchange, 'fetch_open_interest'):
                result = self.exchange.fetch_open_interest(symbol)
                return float(result.get('openInterestAmount', 0))
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка получения OI: {e}")
            return None
    
    async def _fetch_oi_history(self, symbol: str, periods: int = 24) -> List[float]:
        """Получить историю Open Interest"""
        try:
            if self.exchange and hasattr(self.exchange, 'fetch_open_interest_history'):
                history = self.exchange.fetch_open_interest_history(
                    symbol,
                    timeframe='1h',
                    limit=periods
                )
                return [float(item.get('openInterestAmount', 0)) for item in history]
            
            return []
            
        except Exception as e:
            logger.error(f"Ошибка получения истории OI: {e}")
            return []
    
    def _analyze_oi_trend(self, current_oi: float, history: List[float]) -> str:
        """Анализ тренда Open Interest"""
        if not history or len(history) < 2:
            return 'unknown'
        
        # Средний OI за период
        avg_oi = sum(history) / len(history)
        
        # Сравнение с текущим
        if current_oi > avg_oi * 1.1:
            return 'increasing'
        elif current_oi < avg_oi * 0.9:
            return 'decreasing'
        else:
            return 'stable'
    
    async def get_top_funding_rates(self, limit: int = 10) -> List[Dict]:
        """
        Получить топ монет по funding rate
        
        Args:
            limit: Количество монет
        
        Returns:
            Список монет с самыми высокими FR
        """
        try:
            if not self.exchange:
                self._init_exchange()
            
            # Получаем список всех futures рынков
            markets = self.exchange.load_markets()
            future_symbols = [
                symbol for symbol, market in markets.items()
                if market.get('future') and market.get('quote') == 'USDT'
            ]
            
            # Собираем funding rates
            funding_data = []
            
            for symbol in future_symbols[:50]:  # Ограничим количество для производительности
                try:
                    fr_data = await self.get_funding_rate(symbol)
                    if 'error' not in fr_data:
                        funding_data.append(fr_data)
                except Exception as e:
                    logger.debug(f"Пропуск {symbol}: {e}")
                    continue
            
            # Сортируем по абсолютному значению FR
            funding_data.sort(
                key=lambda x: abs(x.get('funding_rate', 0)),
                reverse=True
            )
            
            return funding_data[:limit]
            
        except Exception as e:
            logger.error(f"Ошибка получения топ funding rates: {e}")
            return []
    
    def analyze_market_sentiment(self, funding_rate: float, oi_trend: str, price_change: float) -> Dict:
        """
        Комплексный анализ настроения рынка
        
        Args:
            funding_rate: Текущий funding rate
            oi_trend: Тренд open interest
            price_change: Изменение цены в %
        
        Returns:
            Анализ рыночного настроения
        """
        sentiment_score = 0
        signals = []
        
        # Анализ Funding Rate
        if funding_rate > 0.001:
            sentiment_score += 1
            if funding_rate > 0.01:
                signals.append('⚠️ Экстремально высокий FR - возможна коррекция')
        elif funding_rate < -0.001:
            sentiment_score -= 1
            if funding_rate < -0.01:
                signals.append('⚠️ Экстремально низкий FR - возможен отскок')
        
        # Анализ OI + Price
        if oi_trend == 'increasing' and price_change > 0:
            signals.append('✅ OI растет + цена растет = сильный тренд вверх')
            sentiment_score += 2
        elif oi_trend == 'increasing' and price_change < 0:
            signals.append('⚠️ OI растет + цена падает = сильный тренд вниз')
            sentiment_score -= 2
        elif oi_trend == 'decreasing' and abs(price_change) > 2:
            signals.append('📉 OI падает при движении цены = возможный разворот')
        
        # Общее настроение
        if sentiment_score > 2:
            overall = 'strong_bullish'
        elif sentiment_score > 0:
            overall = 'bullish'
        elif sentiment_score < -2:
            overall = 'strong_bearish'
        elif sentiment_score < 0:
            overall = 'bearish'
        else:
            overall = 'neutral'
        
        return {
            'overall_sentiment': overall,
            'sentiment_score': sentiment_score,
            'signals': signals
        }
    
    def format_funding_rate(self, data: Dict) -> str:
        """Форматировать Funding Rate для отображения"""
        if 'error' in data:
            return f"❌ Ошибка: {data['error']}"
        
        symbol = data.get('symbol', 'N/A')
        fr = data.get('funding_rate', 0)
        ann_rate = data.get('annualized_rate', 0)
        sentiment = data.get('sentiment', 'neutral')
        
        # Emoji для sentiment
        sentiment_emoji = {
            'extremely_bullish': '🔥',
            'bullish': '📈',
            'neutral': '➖',
            'bearish': '📉',
            'extremely_bearish': '❄️'
        }.get(sentiment, '➖')
        
        text = f"💰 <b>Funding Rate: {symbol}</b>\n\n"
        text += f"<b>Текущая ставка:</b> {fr:+.4f}%\n"
        text += f"<b>Годовая (APR):</b> {ann_rate:+.2f}%\n"
        text += f"{sentiment_emoji} <b>Настроение:</b> {sentiment.replace('_', ' ').title()}\n"
        
        if abs(fr) > 1:
            text += f"\n⚠️ <b>Экстремальное значение!</b> Возможна коррекция."
        
        return text
    
    def format_open_interest(self, data: Dict) -> str:
        """Форматировать Open Interest для отображения"""
        if 'error' in data:
            return f"❌ Ошибка: {data['error']}"
        
        symbol = data.get('symbol', 'N/A')
        oi = data.get('open_interest', 0)
        trend = data.get('oi_trend', 'unknown')
        
        # Emoji для тренда
        trend_emoji = {
            'increasing': '📈',
            'decreasing': '📉',
            'stable': '➖',
            'unknown': '❓'
        }.get(trend, '❓')
        
        text = f"📊 <b>Open Interest: {symbol}</b>\n\n"
        text += f"<b>Текущий OI:</b> {oi:,.2f}\n"
        text += f"{trend_emoji} <b>Тренд:</b> {trend.title()}\n"
        
        return text
