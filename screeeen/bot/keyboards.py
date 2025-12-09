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
            [KeyboardButton("🌟 Расширенные функции"), KeyboardButton("❓ Помощь")],
            [KeyboardButton("ℹ️ О боте")]
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
    
    # === NEW v2.0 Keyboards ===
    
    @staticmethod
    def get_advanced_menu() -> InlineKeyboardMarkup:
        """Расширенное меню v2.0 функций"""
        keyboard = [
            [InlineKeyboardButton("🔔 Мои алерты", callback_data="menu_alerts")],
            [InlineKeyboardButton("💼 Портфель", callback_data="menu_portfolio")],
            [InlineKeyboardButton("📌 Подписки", callback_data="menu_subscriptions")],
            [InlineKeyboardButton("📊 MTF Анализ", callback_data="menu_mtf")],
            [InlineKeyboardButton("🔗 Корреляция", callback_data="menu_correlation")],
            [InlineKeyboardButton("💰 Funding Rates", callback_data="menu_funding")],
            [InlineKeyboardButton("⏰ Расписание", callback_data="menu_schedule")],
            [InlineKeyboardButton("◀️ Главное меню", callback_data="main_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_alert_actions_keyboard(alert_id: int) -> InlineKeyboardMarkup:
        """Действия с алертом"""
        keyboard = [
            [InlineKeyboardButton("🗑 Удалить алерт", callback_data=f"delete_alert:{alert_id}")],
            [InlineKeyboardButton("◀️ К списку алертов", callback_data="menu_alerts")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_portfolio_actions_keyboard(position_id: int) -> InlineKeyboardMarkup:
        """Действия с позицией в портфеле"""
        keyboard = [
            [InlineKeyboardButton("🔄 Обновить P&L", callback_data=f"refresh_position:{position_id}")],
            [InlineKeyboardButton("🗑 Удалить позицию", callback_data=f"delete_position:{position_id}")],
            [InlineKeyboardButton("◀️ К портфелю", callback_data="menu_portfolio")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_subscription_keyboard(symbols: List[str] = None) -> InlineKeyboardMarkup:
        """Управление подписками"""
        if symbols is None:
            symbols = []
        
        keyboard = []
        
        # Популярные монеты для подписки
        popular = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT']
        
        for symbol in popular:
            is_subscribed = symbol in symbols
            prefix = "✅" if is_subscribed else "➕"
            action = "unsub" if is_subscribed else "sub"
            keyboard.append([
                InlineKeyboardButton(
                    f"{prefix} {symbol}",
                    callback_data=f"{action}:{symbol}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("📝 Показать мои подписки", callback_data="show_subscriptions")
        ])
        keyboard.append([
            InlineKeyboardButton("◀️ Назад", callback_data="advanced_menu")
        ])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_mtf_timeframes_keyboard() -> InlineKeyboardMarkup:
        """Выбор монеты для MTF анализа"""
        keyboard = [
            [InlineKeyboardButton("BTC/USDT", callback_data="mtf:BTC/USDT")],
            [InlineKeyboardButton("ETH/USDT", callback_data="mtf:ETH/USDT")],
            [InlineKeyboardButton("BNB/USDT", callback_data="mtf:BNB/USDT")],
            [InlineKeyboardButton("📝 Ввести свой символ", callback_data="mtf_custom")],
            [InlineKeyboardButton("◀️ Назад", callback_data="advanced_menu")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def get_schedule_keyboard(active_schedule: bool = False) -> InlineKeyboardMarkup:
        """Управление расписанием"""
        keyboard = []
        
        if active_schedule:
            keyboard.append([InlineKeyboardButton("🔴 Остановить автосканирование", callback_data="stop_schedule")])
        else:
            keyboard.extend([
                [InlineKeyboardButton("30 минут", callback_data="schedule:30:15m")],
                [InlineKeyboardButton("1 час", callback_data="schedule:60:15m")],
                [InlineKeyboardButton("4 часа", callback_data="schedule:240:1h")],
                [InlineKeyboardButton("24 часа", callback_data="schedule:1440:4h")]
            ])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="advanced_menu")])
        
        return InlineKeyboardMarkup(keyboard)