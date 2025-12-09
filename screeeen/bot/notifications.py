from typing import Dict, List
from telegram.constants import ParseMode
from config.settings import SIGNAL_TYPES


class NotificationFormatter:
    """Форматирование уведомлений для Telegram"""

    # Максимальная длина сообщения Telegram
    MAX_MESSAGE_LENGTH = 4000

    @staticmethod
    def format_signal(signal: Dict, compact: bool = False) -> str:
        """Форматировать сигнал для отправки"""

        emoji_map = {
            'structure_break': '🔨',
            'level_approach': '📍',
            'breakout': '🚀',
            'false_breakout': '⚠️',
            'imbalance': '⚡',
            'order_block': '🎯',
            'liquidity_sweep': '💧',
            'divergence': '📊',
            'pattern': '📐',
            'volume_spike': '📢',
            'confluence': '⭐'
        }

        direction_emoji = {
            'bullish': '🟢',
            'bearish': '🔴',
            'neutral': '⚪'
        }

        priority_emoji = {
            'critical': '🚨',
            'high': '❗',
            'medium': '⚠️',
            'low': 'ℹ️'
        }

        signal_type = signal.get('type', 'unknown')
        direction = signal.get('direction', 'neutral')
        priority = signal.get('priority', 'medium')

        # Заголовок
        message = f"{emoji_map.get(signal_type, '📌')} <b>{SIGNAL_TYPES.get(signal_type, signal_type)}</b>\n\n"

        # Символ и цена
        message += f"💱 <b>Пара:</b> <code>{signal['symbol']}</code>\n"
        message += f"💵 <b>Цена:</b> <code>${signal['price']:.4f}</code>\n"

        # Направление и приоритет
        message += f"📊 <b>Направление:</b> {direction_emoji.get(direction, '⚪')} {direction.upper()}\n"
        message += f"{priority_emoji.get(priority, 'ℹ️')} <b>Приоритет:</b> {priority.upper()}\n\n"

        # Тренд
        if 'trend' in signal and signal['trend']:
            trend = signal['trend']
            if isinstance(trend, dict):
                trend_text = trend.get('trend', 'unknown')
                strength = trend.get('strength', 0)
            else:
                trend_text = str(trend)
                strength = 0

            trend_emoji = '📈' if trend_text == 'bullish' else '📉' if trend_text == 'bearish' else '➡️'
            message += f"{trend_emoji} <b>Тренд:</b> {trend_text}"
            if strength:
                message += f" ({strength}%)"
            message += "\n"

        # Индикаторы (если не compact режим)
        if not compact:
            if 'rsi' in signal and signal['rsi']:
                rsi = signal['rsi']
                rsi_status = '🔴 Перекуплен' if rsi > 70 else '🟢 Перепродан' if rsi < 30 else '⚪ Нейтрален'
                message += f"📊 <b>RSI:</b> <code>{rsi:.1f}</code> {rsi_status}\n"

            if 'strength_index' in signal and signal['strength_index']:
                message += f"💪 <b>Сила:</b> <code>{signal['strength_index']:.0f}/100</code>\n"

        message += "\n"

        # Детали сигнала (сокращенные)
        details_text = NotificationFormatter._format_signal_details(signal, compact=compact)

        # Проверяем длину
        full_message = message + details_text

        # Если сообщение слишком длинное, обрезаем детали
        if len(full_message) > NotificationFormatter.MAX_MESSAGE_LENGTH:
            # Возвращаем компактную версию
            return NotificationFormatter.format_signal(signal, compact=True)

        return full_message

    @staticmethod
    def _format_signal_details(signal: Dict, compact: bool = False) -> str:
        """Форматировать детали сигнала"""
        details = signal.get('details', {})
        signal_type = signal.get('type')

        if compact:
            # Компактная версия - только самое важное
            return NotificationFormatter._format_compact_details(signal_type, details)

        detail_text = "<b>Детали:</b>\n"

        if signal_type == 'structure_break':
            if 'bullish' in details.get('type', ''):
                detail_text += f"• Пробой максимума\n"
                if 'new_high' in details:
                    detail_text += f"• Новый хай: <code>${details['new_high']:.4f}</code>\n"
            else:
                detail_text += f"• Пробой минимума\n"
                if 'new_low' in details:
                    detail_text += f"• Новый лоу: <code>${details['new_low']:.4f}</code>\n"
            if 'strength' in details:
                detail_text += f"• Сила: <code>{details['strength']:.2f}%</code>\n"

        elif signal_type == 'level_approach':
            level_type = details.get('level_type', 'level')
            detail_text += f"• Тип: {level_type.capitalize()}\n"
            if 'level_price' in details:
                detail_text += f"• Уровень: <code>${details['level_price']:.4f}</code>\n"
            if 'distance_percent' in details:
                detail_text += f"• Расстояние: <code>{details['distance_percent']:.2f}%</code>\n"

        elif signal_type == 'breakout':
            confirmed = '✅' if details.get('volume_confirmed') else '❌'
            detail_text += f"• Подтверждение объемом: {confirmed}\n"
            if 'broken_level' in details:
                detail_text += f"• Уровень: <code>${details['broken_level']:.4f}</code>\n"
            if 'volume_ratio' in details:
                detail_text += f"• Объем: <code>{details['volume_ratio']:.1f}x</code>\n"

        elif signal_type == 'false_breakout':
            detail_text += f"• Ложный {details.get('level_type', 'пробой')}\n"
            if 'failed_level' in details:
                detail_text += f"• Уровень: <code>${details['failed_level']:.4f}</code>\n"

        elif signal_type == 'imbalance':
            detail_text += f"• Fair Value Gap (FVG)\n"
            if 'size' in details:
                detail_text += f"• Размер: <code>{details['size']:.2f}%</code>\n"

        elif signal_type == 'order_block':
            detail_text += f"• Order Block зона\n"
            if 'strength' in details:
                detail_text += f"• Сила: <code>{details['strength']:.2f}%</code>\n"

        elif signal_type == 'liquidity_sweep':
            detail_text += f"• Liquidity Sweep\n"
            if 'liquidity_level' in details:
                detail_text += f"• Уровень: <code>${details['liquidity_level']:.4f}</code>\n"

        elif signal_type == 'divergence':
            indicator = details.get('indicator', 'RSI')
            detail_text += f"• {indicator} дивергенция\n"

        elif signal_type == 'pattern':
            pattern_type = details.get('type', 'unknown')
            detail_text += f"• {pattern_type.replace('_', ' ').title()}\n"
            reliability = details.get('reliability', 'medium')
            detail_text += f"• Надежность: {reliability.upper()}\n"

        elif signal_type == 'volume_spike':
            if 'ratio' in details:
                detail_text += f"• Объем: <code>{details['ratio']:.1f}x среднего</code>\n"

        elif signal_type == 'confluence':
            factors = details.get('factors_count', 0)
            detail_text += f"• Факторов: <code>{factors}</code>\n"
            signal_types = details.get('signal_types', [])
            if signal_types and len(signal_types) <= 3:
                for stype in signal_types[:3]:
                    emoji = NotificationFormatter._get_signal_emoji(stype)
                    detail_text += f"  {emoji} {SIGNAL_TYPES.get(stype, stype)}\n"

        return detail_text

    @staticmethod
    def _format_compact_details(signal_type: str, details: Dict) -> str:
        """Компактная версия деталей"""
        text = "<b>Детали:</b> "

        if signal_type == 'structure_break':
            strength = details.get('strength', 0)
            text += f"Сила {strength:.1f}%"
        elif signal_type == 'level_approach':
            distance = details.get('distance_percent', 0)
            text += f"Расстояние {distance:.1f}%"
        elif signal_type == 'breakout':
            confirmed = '✅' if details.get('volume_confirmed') else '❌'
            text += f"Объем {confirmed}"
        elif signal_type == 'confluence':
            factors = details.get('factors_count', 0)
            text += f"{factors} факторов"
        else:
            text += "См. график"

        return text + "\n"

    @staticmethod
    def _get_signal_emoji(signal_type: str) -> str:
        """Получить эмодзи для типа сигнала"""
        emojis = {
            'structure_break': '🔨',
            'level_approach': '📍',
            'breakout': '🚀',
            'false_breakout': '⚠️',
            'imbalance': '⚡',
            'order_block': '🎯',
            'liquidity_sweep': '💧',
            'divergence': '📊',
            'pattern': '📐',
            'volume_spike': '📢',
            'confluence': '⭐'
        }
        return emojis.get(signal_type, '📌')

    @staticmethod
    def format_batch_signals(signals: List[Dict]) -> str:
        """Форматировать пакет сигналов"""
        if not signals:
            return "Сигналов не найдено."

        message = f"📊 <b>Найдено сигналов: {len(signals)}</b>\n\n"

        for i, signal in enumerate(signals[:10], 1):
            emoji = NotificationFormatter._get_signal_emoji(signal['type'])
            direction_emoji = '🟢' if signal['direction'] == 'bullish' else '🔴' if signal[
                                                                                      'direction'] == 'bearish' else '⚪'

            message += f"{i}. {emoji} <b>{signal['symbol']}</b> {direction_emoji}\n"
            message += f"   {SIGNAL_TYPES.get(signal['type'], signal['type'])}\n"
            message += f"   💵 ${signal['price']:.4f}\n\n"

        if len(signals) > 10:
            message += f"\n... и еще {len(signals) - 10} сигналов"

        return message