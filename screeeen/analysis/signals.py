import pandas as pd
from typing import List, Dict, Optional
from loguru import logger
from datetime import datetime

from analysis.technical import TechnicalAnalysis
from analysis.patterns import PatternRecognition
from analysis.smart_money import SmartMoneyAnalysis
from data.data_processor import DataProcessor
from config.settings import SHOW_CONFLUENCE, MAX_SIGNALS_PER_COIN


class SignalGenerator:
    """Генерация торговых сигналов на основе всех типов анализа"""

    def __init__(self):
        self.technical = TechnicalAnalysis()
        self.patterns = PatternRecognition()
        self.smart_money = SmartMoneyAnalysis()
        self.processor = DataProcessor()

    async def analyze_symbol(
            self,
            df: pd.DataFrame,
            symbol: str,
            levels: Dict,
            enabled_signals: List[str] = None
    ) -> List[Dict]:
        """Комплексный анализ символа и генерация сигналов"""

        if df is None or len(df) < 20:
            return []

        all_signals = []
        current_price = df['close'].iloc[-1]

        # Если не указаны типы сигналов, используем все
        if enabled_signals is None:
            enabled_signals = [
                'structure_break', 'level_approach', 'breakout',
                'false_breakout', 'imbalance', 'order_block',
                'liquidity_sweep', 'divergence', 'pattern',
                'volume_spike', 'confluence'
            ]

        try:
            # 1. Слом структуры (Structure Break) - ОГРАНИЧИВАЕМ
            if 'structure_break' in enabled_signals:
                bos_signals = self.smart_money.detect_break_of_structure(df)
                for bos in bos_signals[-2:]:  # Только последние 2
                    all_signals.append(self._create_signal(
                        symbol=symbol,
                        signal_type='structure_break',
                        direction='bullish' if 'bullish' in bos['type'] else 'bearish',
                        price=current_price,
                        details=bos,
                        priority='high'
                    ))

            # 2. Поджим к уровню (Level Approach)
            if 'level_approach' in enabled_signals:
                approach_signals = self._check_level_approach(df, levels, current_price, symbol)
                all_signals.extend(approach_signals[:3])  # Максимум 3

            # 3. Пробой уровня (Breakout)
            if 'breakout' in enabled_signals:
                breakout_signals = self._check_breakouts(df, levels, current_price, symbol)
                all_signals.extend(breakout_signals[:2])  # Максимум 2

            # 4. Ложный пробой (False Breakout)
            if 'false_breakout' in enabled_signals:
                false_breakout_signals = self._check_false_breakouts(df, levels, symbol)
                all_signals.extend(false_breakout_signals[:2])  # Максимум 2

            # 5. Имбаланс / FVG (Fair Value Gap) - ОГРАНИЧИВАЕМ
            if 'imbalance' in enabled_signals:
                fvgs = self.smart_money.find_fair_value_gaps(df)
                # Только последние 3 незаполненных FVG
                for fvg in fvgs[-3:]:
                    if not fvg.get('filled'):
                        all_signals.append(self._create_signal(
                            symbol=symbol,
                            signal_type='imbalance',
                            direction=fvg['type'],
                            price=current_price,
                            details=fvg,
                            priority='medium'
                        ))

            # 6. Order Block - ОГРАНИЧИВАЕМ
            if 'order_block' in enabled_signals:
                order_blocks = self.smart_money.find_order_blocks(df)
                # Только последние 2 самых сильных
                sorted_ob = sorted(order_blocks, key=lambda x: x.get('strength', 0), reverse=True)
                for ob in sorted_ob[:2]:
                    all_signals.append(self._create_signal(
                        symbol=symbol,
                        signal_type='order_block',
                        direction=ob['type'],
                        price=current_price,
                        details=ob,
                        priority='high'
                    ))

            # 7. Liquidity Sweep
            if 'liquidity_sweep' in enabled_signals:
                liquidity_zones = self.smart_money.find_liquidity_zones(df)
                sweeps = self.smart_money.detect_liquidity_sweep(df, liquidity_zones)
                for sweep in sweeps[:2]:  # Максимум 2
                    all_signals.append(self._create_signal(
                        symbol=symbol,
                        signal_type='liquidity_sweep',
                        direction='bullish' if 'bullish' in sweep['type'] else 'bearish',
                        price=current_price,
                        details=sweep,
                        priority='high'
                    ))

            # 8. Дивергенции (Divergence)
            if 'divergence' in enabled_signals:
                rsi_div = self.technical.find_rsi_divergence(df)
                macd_div = self.technical.find_macd_divergence(df)

                for div in (rsi_div + macd_div)[:2]:  # Максимум 2
                    all_signals.append(self._create_signal(
                        symbol=symbol,
                        signal_type='divergence',
                        direction=div['type'],
                        price=current_price,
                        details=div,
                        priority='high'
                    ))

            # 9. Графические паттерны (Patterns) - ОГРАНИЧИВАЕМ
            if 'pattern' in enabled_signals:
                triangles = self.patterns.find_triangles(df)
                head_shoulders = self.patterns.find_head_and_shoulders(df)
                flags = self.patterns.find_flags_and_pennants(df)
                double_patterns = self.patterns.find_double_top_bottom(df)
                candle_patterns = self.patterns.detect_candlestick_patterns(df)

                # Берем только высоконадежные паттерны
                all_patterns = triangles + head_shoulders + flags + double_patterns + candle_patterns
                high_reliability = [p for p in all_patterns if p.get('reliability') in ['high', 'medium']]

                for pattern in high_reliability[:3]:  # Максимум 3
                    all_signals.append(self._create_signal(
                        symbol=symbol,
                        signal_type='pattern',
                        direction=pattern.get('direction', 'neutral'),
                        price=current_price,
                        details=pattern,
                        priority='medium' if pattern.get('reliability') == 'high' else 'low'
                    ))

            # 10. Объемные аномалии (Volume Spike)
            if 'volume_spike' in enabled_signals:
                volume_anomaly = self.processor.detect_volume_anomaly(df)
                if volume_anomaly and volume_anomaly['is_anomaly']:
                    all_signals.append(self._create_signal(
                        symbol=symbol,
                        signal_type='volume_spike',
                        direction='neutral',
                        price=current_price,
                        details=volume_anomaly,
                        priority='medium'
                    ))

            # Добавляем дополнительную информацию ко всем сигналам
            for signal in all_signals:
                trend = self.technical.detect_trend(df)
                signal['trend'] = trend
                signal['strength_index'] = self.technical.calculate_strength_index(df)

                # RSI и MACD индикаторы
                if 'rsi' in df.columns:
                    signal['rsi'] = round(df['rsi'].iloc[-1], 2)
                if 'macd' in df.columns:
                    signal['macd'] = round(df['macd'].iloc[-1], 4)

            # 11. Confluence зоны - ОПЦИОНАЛЬНО (отключено по умолчанию)
            if SHOW_CONFLUENCE and 'confluence' in enabled_signals and len(all_signals) >= 3:
                confluence_signals = self._find_confluence_zones(all_signals, df, current_price, symbol)
                if confluence_signals:
                    all_signals.extend(confluence_signals)

        except Exception as e:
            logger.error(f"Ошибка анализа {symbol}: {e}")

        # ВАЖНО: Ограничиваем общее количество сигналов на монету
        return all_signals[:MAX_SIGNALS_PER_COIN]

    def _create_signal(self, symbol: str, signal_type: str, direction: str, price: float, details: Dict,
                       priority: str) -> Dict:
        """Создать структуру сигнала с обязательными полями"""
        return {
            'symbol': symbol,
            'type': signal_type,
            'direction': direction,
            'price': price,
            'details': details,
            'priority': priority,
            'timestamp': datetime.now()
        }

    def _check_level_approach(self, df: pd.DataFrame, levels: Dict, current_price: float, symbol: str) -> List[Dict]:
        """Проверка поджима к уровням"""
        signals = []
        threshold = 0.015  # 1.5% от цены

        # Проверка поддержки
        for support in levels.get('support', [])[:3]:  # Только топ-3
            distance = abs(current_price - support) / current_price
            if distance < threshold:
                signals.append(self._create_signal(
                    symbol=symbol,
                    signal_type='level_approach',
                    direction='bullish',
                    price=current_price,
                    details={
                        'level_type': 'support',
                        'level_price': support,
                        'distance_percent': round(distance * 100, 2)
                    },
                    priority='high'
                ))

        # Проверка сопротивления
        for resistance in levels.get('resistance', [])[:3]:  # Только топ-3
            distance = abs(current_price - resistance) / current_price
            if distance < threshold:
                signals.append(self._create_signal(
                    symbol=symbol,
                    signal_type='level_approach',
                    direction='bearish',
                    price=current_price,
                    details={
                        'level_type': 'resistance',
                        'level_price': resistance,
                        'distance_percent': round(distance * 100, 2)
                    },
                    priority='high'
                ))

        return signals

    def _check_breakouts(self, df: pd.DataFrame, levels: Dict, current_price: float, symbol: str) -> List[Dict]:
        """Проверка пробоев уровней"""
        signals = []

        if len(df) < 2:
            return signals

        prev_price = df['close'].iloc[-2]
        current_volume = df['volume'].iloc[-1]
        avg_volume = df['volume'].tail(20).mean()

        # Пробой сопротивления
        for resistance in levels.get('resistance', [])[:2]:
            if prev_price < resistance and current_price > resistance:
                volume_confirm = current_volume > avg_volume * 1.5

                signals.append(self._create_signal(
                    symbol=symbol,
                    signal_type='breakout',
                    direction='bullish',
                    price=current_price,
                    details={
                        'broken_level': resistance,
                        'volume_confirmed': volume_confirm,
                        'volume_ratio': round(current_volume / avg_volume, 2)
                    },
                    priority='high' if volume_confirm else 'medium'
                ))

        # Пробой поддержки
        for support in levels.get('support', [])[:2]:
            if prev_price > support and current_price < support:
                volume_confirm = current_volume > avg_volume * 1.5

                signals.append(self._create_signal(
                    symbol=symbol,
                    signal_type='breakout',
                    direction='bearish',
                    price=current_price,
                    details={
                        'broken_level': support,
                        'volume_confirmed': volume_confirm,
                        'volume_ratio': round(current_volume / avg_volume, 2)
                    },
                    priority='high' if volume_confirm else 'medium'
                ))

        return signals

    def _check_false_breakouts(self, df: pd.DataFrame, levels: Dict, symbol: str) -> List[Dict]:
        """Проверка ложных пробоев"""
        signals = []

        if len(df) < 5:
            return signals

        recent = df.tail(5)
        current_price = df['close'].iloc[-1]

        # Ложный пробой сопротивления (цена пробила, но вернулась)
        for resistance in levels.get('resistance', [])[:2]:
            if (recent['high'].max() > resistance and
                    current_price < resistance and
                    recent['close'].iloc[-2] > resistance):
                signals.append(self._create_signal(
                    symbol=symbol,
                    signal_type='false_breakout',
                    direction='bearish',
                    price=current_price,
                    details={
                        'failed_level': resistance,
                        'level_type': 'resistance',
                        'fake_high': recent['high'].max()
                    },
                    priority='high'
                ))

        # Ложный пробой поддержки
        for support in levels.get('support', [])[:2]:
            if (recent['low'].min() < support and
                    current_price > support and
                    recent['close'].iloc[-2] < support):
                signals.append(self._create_signal(
                    symbol=symbol,
                    signal_type='false_breakout',
                    direction='bullish',
                    price=current_price,
                    details={
                        'failed_level': support,
                        'level_type': 'support',
                        'fake_low': recent['low'].min()
                    },
                    priority='high'
                ))

        return signals

    def _find_confluence_zones(self, signals: List[Dict], df: pd.DataFrame, current_price: float, symbol: str) -> List[
        Dict]:
        """Поиск зон совпадения нескольких факторов"""
        confluence_signals = []

        # Группируем сигналы по направлению
        bullish_signals = [s for s in signals if s.get('direction') == 'bullish']
        bearish_signals = [s for s in signals if s.get('direction') == 'bearish']

        # Создаем confluence ТОЛЬКО если есть минимум 3 разных типа сигналов
        bullish_types = set(s['type'] for s in bullish_signals)
        bearish_types = set(s['type'] for s in bearish_signals)

        # Бычий confluence
        if len(bullish_types) >= 3:
            confluence_signals.append(self._create_signal(
                symbol=symbol,
                signal_type='confluence',
                direction='bullish',
                price=current_price,
                details={
                    'factors_count': len(bullish_signals),
                    'unique_types': len(bullish_types),
                    'signal_types': list(bullish_types),
                    'description': f'Совпадение {len(bullish_types)} типов бычьих сигналов'
                },
                priority='critical'
            ))

        # Медвежий confluence
        if len(bearish_types) >= 3:
            confluence_signals.append(self._create_signal(
                symbol=symbol,
                signal_type='confluence',
                direction='bearish',
                price=current_price,
                details={
                    'factors_count': len(bearish_signals),
                    'unique_types': len(bearish_types),
                    'signal_types': list(bearish_types),
                    'description': f'Совпадение {len(bearish_types)} типов медвежьих сигналов'
                },
                priority='critical'
            ))

        return confluence_signals