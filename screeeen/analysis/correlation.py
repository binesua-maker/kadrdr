"""
Correlation Analysis - Корреляционный анализ
"""
from typing import Dict, List, Optional, Tuple
from loguru import logger
import pandas as pd
import numpy as np
from data.binance_client import BinanceDataClient


class CorrelationAnalyzer:
    """Анализ корреляции между монетами"""
    
    def __init__(self):
        self.binance = BinanceDataClient()
        self.btc_symbol = 'BTC/USDT'
    
    async def analyze_correlation_with_btc(self, symbol: str, timeframe: str = '1h', periods: int = 100) -> Dict:
        """
        Анализ корреляции монеты с BTC
        
        Args:
            symbol: Символ монеты
            timeframe: Таймфрейм
            periods: Количество периодов для анализа
        
        Returns:
            Словарь с результатами корреляции
        """
        try:
            # Получаем данные для обеих монет
            symbol_df = await self.binance.get_ohlcv(symbol, timeframe, limit=periods)
            btc_df = await self.binance.get_ohlcv(self.btc_symbol, timeframe, limit=periods)
            
            if symbol_df is None or btc_df is None:
                return {'error': 'Не удалось получить данные'}
            
            if len(symbol_df) < 20 or len(btc_df) < 20:
                return {'error': 'Недостаточно данных'}
            
            # Выравниваем данные по времени
            merged = pd.merge(
                symbol_df[['timestamp', 'close']],
                btc_df[['timestamp', 'close']],
                on='timestamp',
                suffixes=('_symbol', '_btc')
            )
            
            if len(merged) < 20:
                return {'error': 'Недостаточно совпадающих данных'}
            
            # Рассчитываем процентные изменения
            merged['returns_symbol'] = merged['close_symbol'].pct_change()
            merged['returns_btc'] = merged['close_btc'].pct_change()
            
            # Корреляция Пирсона
            correlation = merged['returns_symbol'].corr(merged['returns_btc'])
            
            # Статистика
            symbol_volatility = merged['returns_symbol'].std() * 100
            btc_volatility = merged['returns_btc'].std() * 100
            
            # Определяем тип корреляции
            correlation_type = self._get_correlation_type(correlation)
            
            # Дивергенция (расхождение)
            divergence_score = self._calculate_divergence(merged)
            
            return {
                'symbol': symbol,
                'btc_symbol': self.btc_symbol,
                'correlation': round(float(correlation), 3),
                'correlation_type': correlation_type,
                'symbol_volatility': round(symbol_volatility, 3),
                'btc_volatility': round(btc_volatility, 3),
                'divergence_score': round(divergence_score, 3),
                'periods_analyzed': len(merged),
                'timeframe': timeframe
            }
            
        except Exception as e:
            logger.error(f"Ошибка анализа корреляции для {symbol}: {e}")
            return {'error': str(e)}
    
    def _get_correlation_type(self, correlation: float) -> str:
        """Определить тип корреляции"""
        if pd.isna(correlation):
            return 'unknown'
        
        if correlation > 0.7:
            return 'strong_positive'
        elif correlation > 0.3:
            return 'moderate_positive'
        elif correlation > -0.3:
            return 'weak'
        elif correlation > -0.7:
            return 'moderate_negative'
        else:
            return 'strong_negative'
    
    def _calculate_divergence(self, merged_df: pd.DataFrame) -> float:
        """
        Рассчитать дивергенцию (расхождение в движении)
        Положительное значение = монета опережает BTC
        Отрицательное = отстает
        """
        try:
            # Кумулятивные возвраты
            merged_df['cum_returns_symbol'] = (1 + merged_df['returns_symbol']).cumprod()
            merged_df['cum_returns_btc'] = (1 + merged_df['returns_btc']).cumprod()
            
            # Последние значения
            last_symbol = merged_df['cum_returns_symbol'].iloc[-1]
            last_btc = merged_df['cum_returns_btc'].iloc[-1]
            
            # Дивергенция в процентах
            divergence = ((last_symbol - last_btc) / last_btc) * 100
            
            return float(divergence)
            
        except Exception:
            return 0.0
    
    async def find_divergent_coins(
        self,
        symbols: List[str],
        timeframe: str = '1h',
        min_divergence: float = 5.0
    ) -> List[Dict]:
        """
        Найти монеты с сильной дивергенцией от BTC
        
        Args:
            symbols: Список символов для анализа
            timeframe: Таймфрейм
            min_divergence: Минимальная дивергенция для отбора
        
        Returns:
            Список монет с дивергенцией
        """
        divergent_coins = []
        
        for symbol in symbols:
            try:
                result = await self.analyze_correlation_with_btc(symbol, timeframe)
                
                if 'error' not in result:
                    divergence = result.get('divergence_score', 0)
                    
                    if abs(divergence) >= min_divergence:
                        divergent_coins.append(result)
                        
            except Exception as e:
                logger.error(f"Ошибка анализа {symbol}: {e}")
                continue
        
        # Сортируем по абсолютной дивергенции
        divergent_coins.sort(key=lambda x: abs(x.get('divergence_score', 0)), reverse=True)
        
        return divergent_coins
    
    async def analyze_sector_correlation(
        self,
        sector_symbols: List[str],
        timeframe: str = '1h'
    ) -> Dict:
        """
        Анализ корреляции внутри сектора (например, DeFi, L1, L2)
        
        Args:
            sector_symbols: Список символов одного сектора
            timeframe: Таймфрейм
        
        Returns:
            Матрица корреляций и статистика
        """
        try:
            # Получаем данные для всех монет
            all_data = {}
            
            for symbol in sector_symbols:
                df = await self.binance.get_ohlcv(symbol, timeframe, limit=100)
                if df is not None and len(df) >= 20:
                    all_data[symbol] = df[['timestamp', 'close']]
            
            if len(all_data) < 2:
                return {'error': 'Недостаточно данных для анализа'}
            
            # Создаем общий DataFrame
            base_symbol = list(all_data.keys())[0]
            merged = all_data[base_symbol].copy()
            merged = merged.rename(columns={'close': base_symbol})
            
            for symbol, df in all_data.items():
                if symbol != base_symbol:
                    merged = pd.merge(
                        merged,
                        df[['timestamp', 'close']].rename(columns={'close': symbol}),
                        on='timestamp',
                        how='inner'
                    )
            
            # Удаляем timestamp для корреляции
            price_data = merged.drop('timestamp', axis=1)
            
            # Рассчитываем корреляцию
            correlation_matrix = price_data.pct_change().corr()
            
            # Средняя корреляция в секторе
            avg_correlation = correlation_matrix.values[np.triu_indices_from(correlation_matrix.values, k=1)].mean()
            
            return {
                'sector_size': len(all_data),
                'average_correlation': round(float(avg_correlation), 3),
                'correlation_matrix': correlation_matrix.to_dict(),
                'timeframe': timeframe,
                'periods_analyzed': len(merged)
            }
            
        except Exception as e:
            logger.error(f"Ошибка секторного анализа: {e}")
            return {'error': str(e)}
    
    def format_correlation_analysis(self, analysis: Dict) -> str:
        """Форматировать результаты корреляции для отображения"""
        if 'error' in analysis:
            return f"❌ Ошибка: {analysis['error']}"
        
        symbol = analysis.get('symbol', 'N/A')
        corr = analysis.get('correlation', 0)
        corr_type = analysis.get('correlation_type', 'unknown')
        divergence = analysis.get('divergence_score', 0)
        
        # Emoji для корреляции
        corr_emoji = {
            'strong_positive': '🟢',
            'moderate_positive': '🟩',
            'weak': '⚪',
            'moderate_negative': '🟥',
            'strong_negative': '🔴'
        }.get(corr_type, '⚪')
        
        # Emoji для дивергенции
        div_emoji = '📈' if divergence > 0 else '📉' if divergence < 0 else '➖'
        
        text = f"🔗 <b>Корреляция: {symbol}</b>\n\n"
        text += f"{corr_emoji} <b>Корреляция с BTC:</b> {corr:.3f}\n"
        text += f"<b>Тип:</b> {corr_type.replace('_', ' ').title()}\n\n"
        
        text += f"{div_emoji} <b>Дивергенция:</b> {divergence:+.2f}%\n"
        
        if abs(divergence) > 10:
            text += "⚠️ <b>Сильное расхождение с BTC!</b>\n"
        
        text += f"\n<b>Волатильность:</b>\n"
        text += f"  • {symbol}: {analysis.get('symbol_volatility', 0):.3f}%\n"
        text += f"  • BTC: {analysis.get('btc_volatility', 0):.3f}%\n"
        
        text += f"\n<i>Анализ на {analysis.get('timeframe', 'N/A')}, {analysis.get('periods_analyzed', 0)} периодов</i>"
        
        return text
