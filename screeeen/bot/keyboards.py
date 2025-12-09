from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from typing import List

class BotKeyboards:
    """Клавиатуры для Telegram бота"""
    
    @staticmethod
    def get_main_menu() -> ReplyKeyboardMarkup:
        """Главное меню"""
        keyboard = [
            [KeyboardButton("🔍 Запустить скан"), KeyboardButton("⚙️ Настройки")],
            [KeyboardButton("📊 История сигналов"), KeyboardButton("📈 Статистика")],
            [KeyboardButton("❓ Помощь"), KeyboardButton("ℹ️ О боте")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    @staticmethod
    def get_signal_types_keyboard(selected: List[str] = None) -> InlineKeyboardMarkup:
        """Клавиатура выбора типов сигналов"""
        if selected is None:
            selected = []
        
        signal_types = {
            'structure_break': '🔨 Слом структуры',
            'level_approach': '📍 Поджим к уровню',
            'breakout': '🚀 Пробой',
            'false_breakout': '⚠️ Ложный пробой',
            'imbalance': '⚡ Имбаланс (FVG)',
            'order_block': '🎯 Order Block',
            'liquidity_sweep': '💧 Liquidity Sweep',
            'divergence': '📊 Дивергенция',
            'pattern': '📐 Паттерн',
            'volume_spike': '📢 Объемный всплеск',
            'confluence': '⭐ Confluence'
        }
        
        keyboard = []
        
        for signal_id, signal_name in signal_types.items():
            is_selected = signal_id in selected
            prefix = "✅ " if is_selected else "⬜ "
            keyboard.append([
                InlineKeyboardButton(
                    f"{prefix}{signal_name}",
                    callback_data=f"toggle_signal:{signal_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("✅ Выбрать все", callback_data="signal_select_all"),
            InlineKeyboardButton("❌ Снять все", callback_data="signal_deselect_all")
        ])
        
        keyboard.append([
            InlineKeyboardButton("▶️ Начать сканирование", callback_data="start_scan")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_timeframe_keyboard(selected: str = '15m') -> InlineKeyboardMarkup:
        """Клавиатура выбора таймфрейма"""
        timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        
        keyboard = []
        row = []
        
        for tf in timeframes:
            prefix = "✅ " if tf == selected else ""
            row.append(InlineKeyboardButton(
                f"{prefix}{tf}",
                callback_data=f"timeframe:{tf}"
            ))
            
            if len(row) == 3:
                keyboard.append(row)
                row = []
        
        if row:
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("◀️ Назад", callback_data="back_to_settings")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_settings_keyboard() -> InlineKeyboardMarkup:
        """Клавиатура настроек"""
        keyboard = [
            [InlineKeyboardButton("📊 Таймфрейм", callback_data="settings_timeframe")],
            [InlineKeyboardButton("🎯 Типы сигналов", callback_data="settings_signals")],
            [InlineKeyboardButton("🔔 Уведомления", callback_data="settings_notifications")],
            [InlineKeyboardButton("💰 Минимальный объем", callback_data="settings_volume")],
            [InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_notifications_keyboard(enabled: bool = True) -> InlineKeyboardMarkup:
        """Клавиатура управления уведомлениями"""
        status = "🔔 Включены" if enabled else "🔕 Выключены"
        action = "Выключить" if enabled else "Включить"
        
        keyboard = [
            [InlineKeyboardButton(f"Статус: {status}", callback_data="noop")],
            [InlineKeyboardButton(f"{'🔕' if enabled else '🔔'} {action}", callback_data="toggle_notifications")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_to_settings")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_signal_detail_keyboard(symbol: str) -> InlineKeyboardMarkup:
        """Клавиатура для детального просмотра сигнала"""
        keyboard = [
            [InlineKeyboardButton("📈 Посмотреть график", callback_data=f"chart:{symbol}")],
            [InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh:{symbol}")],
            [InlineKeyboardButton("🔗 Открыть на Binance", url=f"https://www.binance.com/en/trade/{symbol.replace('/', '_')}")],
            [InlineKeyboardButton("◀️ Назад к списку", callback_data="back_to_list")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_scan_control_keyboard(is_scanning: bool = False) -> InlineKeyboardMarkup:
        """Клавиатура управления сканированием"""
        if is_scanning:
            keyboard = [
                [InlineKeyboardButton("⏸ Остановить сканирование", callback_data="stop_scan")],
                [InlineKeyboardButton("🔄 Статус сканирования", callback_data="scan_status")]
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("▶️ Запустить сканирование", callback_data="start_scan")],
                [InlineKeyboardButton("⚙️ Настроить параметры", callback_data="settings_signals")]
            ]
        
        return InlineKeyboardMarkup(keyboard)