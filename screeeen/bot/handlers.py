from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest
from loguru import logger
from datetime import datetime
from typing import List, Dict
import asyncio

from bot.keyboards import BotKeyboards
from bot.notifications import NotificationFormatter
from data.binance_client import BinanceDataClient
from data.data_processor import DataProcessor
from analysis.signals import SignalGenerator
from database.db_manager import DatabaseManager
from config.settings import SIGNAL_TYPES, DEFAULT_TIMEFRAME


class BotHandlers:
    """Обработчики команд Telegram бота"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.keyboards = BotKeyboards()
        self.formatter = NotificationFormatter()
        self.binance = BinanceDataClient()
        self.processor = DataProcessor()
        self.signal_generator = SignalGenerator()
        self.active_scans = {}

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user = update.effective_user

        # Регистрируем пользователя в БД
        await self.db.create_user(user.id, user.username)

        welcome_message = f"""
👋 Привет, {user.first_name}!

Я <b>Crypto Screener Bot</b> - профессиональный инструмент для анализа криптовалют.

🎯 <b>Что я умею:</b>
• Мониторю топ-100 монет на Binance 24/7
• Анализирую графики по Smart Money Concepts
• Нахожу паттерны и разворотные точки
• Определяю зоны ликвидности и Order Blocks
• Отслеживаю пробои и ложные пробои
• Ищу дивергенции и зоны совпадения

⚠️ <b>Внимание:</b> Стейблкоины автоматически исключены из анализа

📊 <b>Типы анализа:</b>
{self._format_signal_types()}

Используй меню ниже для начала работы!
        """

        await update.message.reply_text(
            welcome_message,
            reply_markup=self.keyboards.get_main_menu(),
            parse_mode=ParseMode.HTML
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 <b>Руководство по использованию</b>

<b>Основные команды:</b>
/start - Начать работу с ботом
/scan - Запустить сканирование
/settings - Открыть настройки
/history - Посмотреть историю сигналов
/stats - Статистика по монетам
/help - Показать эту справку

<b>Как пользоваться:</b>
1️⃣ Выбери типы анализа в настройках
2️⃣ Настрой таймфрейм и фильтры
3️⃣ Запусти сканирование
4️⃣ Получай уведомления о сигналах!

<b>Типы сигналов:</b>
🔨 <b>Слом структуры</b> - Break of Structure (BOS)
📍 <b>Поджим к уровню</b> - Цена приближается к важному уровню
🚀 <b>Пробой</b> - Пробой уровня с подтверждением
⚠️ <b>Ложный пробой</b> - Fake breakout, возврат цены
⚡ <b>Имбаланс</b> - Fair Value Gap (FVG)
🎯 <b>Order Block</b> - Зона интереса крупных игроков
💧 <b>Liquidity Sweep</b> - Сбор ликвидности
📊 <b>Дивергенция</b> - RSI/MACD divergence
📐 <b>Паттерн</b> - Графические паттерны
📢 <b>Объемный всплеск</b> - Аномальные объемы
⭐ <b>Зона совпадения</b> - Совпадение нескольких факторов

<b>Поддержка:</b>
По вопросам пишите @binesua_maker
        """

        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

    async def scan_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /scan"""
        user_id = update.effective_user.id
        settings = await self.db.get_user_settings(user_id)

        message = """
🔍 <b>Настройка сканирования</b>

Выберите типы сигналов, которые хотите отслеживать.
Можно выбрать несколько или все сразу.

⚠️ Стейблкоины автоматически исключаются из анализа.
        """

        selected_signals = settings.get('enabled_signals', []) if settings else []

        await update.message.reply_text(
            message,
            reply_markup=self.keyboards.get_signal_types_keyboard(selected_signals),
            parse_mode=ParseMode.HTML
        )

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /settings"""
        user_id = update.effective_user.id
        settings = await self.db.get_user_settings(user_id)

        # Исправленная строка с правильным тернарным оператором
        timeframe = settings.get('timeframe', DEFAULT_TIMEFRAME) if settings else DEFAULT_TIMEFRAME
        notifications = settings.get('notifications_enabled', True) if settings else True
        notifications_text = 'Включены' if notifications else 'Выключены'
        min_volume = settings.get('min_volume', 1000000) if settings else 1000000

        message = f"""
⚙️ <b>Настройки</b>

Текущие параметры:
📊 Таймфрейм: <code>{timeframe}</code>
🔔 Уведомления: <code>{notifications_text}</code>
💰 Мин. объем: <code>${min_volume:,.0f}</code>

Выберите что хотите изменить:
        """

        await update.message.reply_text(
            message,
            reply_markup=self.keyboards.get_settings_keyboard(),
            parse_mode=ParseMode.HTML
        )

    async def history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /history"""
        user_id = update.effective_user.id
        signals = await self.db.get_user_signals(user_id, limit=20)

        if not signals:
            await update.message.reply_text(
                "📭 История сигналов пуста.\n\nЗапустите сканирование, чтобы получать сигналы!"
            )
            return

        message = "📊 <b>История сигналов (последние 20)</b>\n\n"

        for signal in signals:
            emoji = self._get_signal_emoji(signal['type'])
            direction_emoji = "🟢" if signal['direction'] == 'bullish' else "🔴" if signal[
                                                                                      'direction'] == 'bearish' else "⚪"

            message += f"{emoji} <b>{signal['symbol']}</b> {direction_emoji}\n"
            message += f"   {SIGNAL_TYPES.get(signal['type'], signal['type'])}\n"
            message += f"   💵 ${signal['price']:.4f} | ⏰ {signal['timestamp']}\n\n"

        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /stats"""
        user_id = update.effective_user.id
        stats = await self.db.get_user_statistics(user_id)

        message = f"""
📈 <b>Статистика</b>

📊 Всего сигналов: <code>{stats.get('total_signals', 0)}</code>
🟢 Бычьих: <code>{stats.get('bullish_signals', 0)}</code>
🔴 Медвежьих: <code>{stats.get('bearish_signals', 0)}</code>

<b>Топ монет по сигналам:</b>
{self._format_top_coins(stats.get('top_coins', []))}

<b>Популярные типы сигналов:</b>
{self._format_top_signal_types(stats.get('top_signal_types', []))}

📅 Последнее сканирование: <code>{stats.get('last_scan', 'Никогда')}</code>
        """

        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback кнопок"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        data = query.data

        try:
            # Toggle signal type
            if data.startswith('toggle_signal:'):
                signal_type = data.split(':')[1]
                await self._toggle_signal_type(query, user_id, signal_type)

            # Select/Deselect all signals
            elif data == 'signal_select_all':
                await self._select_all_signals(query, user_id)

            elif data == 'signal_deselect_all':
                await self._deselect_all_signals(query, user_id)

            # Start scan
            elif data == 'start_scan':
                await self._start_scan(query, user_id, context)

            # Stop scan
            elif data == 'stop_scan':
                await self._stop_scan(query, user_id)

            # Settings callbacks
            elif data == 'settings_timeframe':
                await self._show_timeframe_settings(query, user_id)

            elif data.startswith('timeframe:'):
                timeframe = data.split(':')[1]
                await self._set_timeframe(query, user_id, timeframe)

            elif data == 'settings_signals':
                await self._show_signal_settings(query, user_id)

            elif data == 'settings_notifications':
                await self._show_notification_settings(query, user_id)

            elif data == 'toggle_notifications':
                await self._toggle_notifications(query, user_id)

            elif data == 'back_to_settings':
                await self._show_settings_menu(query, user_id)

            elif data == 'main_menu':
                await self._show_main_menu(query)

        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                logger.debug("Сообщение не изменилось - игнорируем")
            else:
                logger.error(f"BadRequest ошибка: {e}")
                raise
        except Exception as e:
            logger.error(f"Ошибка обработки callback: {e}")
            await query.answer("❌ Произошла ошибка. Попробуйте еще раз.", show_alert=True)

    async def _toggle_signal_type(self, query, user_id: int, signal_type: str):
        """Переключить тип сигнала"""
        settings = await self.db.get_user_settings(user_id)
        enabled_signals = settings.get('enabled_signals', []) if settings else []

        if signal_type in enabled_signals:
            enabled_signals.remove(signal_type)
            status = "снят"
        else:
            enabled_signals.append(signal_type)
            status = "выбран"

        await self.db.update_user_settings(user_id, {'enabled_signals': enabled_signals})

        try:
            await query.edit_message_reply_markup(
                reply_markup=self.keyboards.get_signal_types_keyboard(enabled_signals)
            )
            signal_name = SIGNAL_TYPES.get(signal_type, signal_type)
            await query.answer(f"{'✅' if status == 'выбран' else '❌'} {signal_name} {status}")
        except BadRequest as e:
            if "message is not modified" not in str(e).lower():
                raise

    async def _select_all_signals(self, query, user_id: int):
        """Выбрать все типы сигналов"""
        settings = await self.db.get_user_settings(user_id)
        enabled_signals = settings.get('enabled_signals', []) if settings else []
        all_signals = list(SIGNAL_TYPES.keys())

        # Проверяем, не выбраны ли уже все сигналы
        if set(enabled_signals) == set(all_signals):
            await query.answer("✅ Все сигналы уже выбраны!", show_alert=True)
            return

        await self.db.update_user_settings(user_id, {'enabled_signals': all_signals})

        try:
            await query.edit_message_reply_markup(
                reply_markup=self.keyboards.get_signal_types_keyboard(all_signals)
            )
            await query.answer("✅ Выбраны все типы сигналов")
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                await query.answer("✅ Все сигналы уже выбраны!", show_alert=True)
            else:
                raise

    async def _deselect_all_signals(self, query, user_id: int):
        """Снять все типы сигналов"""
        settings = await self.db.get_user_settings(user_id)
        enabled_signals = settings.get('enabled_signals', []) if settings else []

        # Проверяем, не сняты ли уже все сигналы
        if not enabled_signals:
            await query.answer("⚠️ Все сигналы уже сняты!", show_alert=True)
            return

        await self.db.update_user_settings(user_id, {'enabled_signals': []})

        try:
            await query.edit_message_reply_markup(
                reply_markup=self.keyboards.get_signal_types_keyboard([])
            )
            await query.answer("✅ Все сигналы сняты")
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                await query.answer("⚠️ Все сигналы уже сняты!", show_alert=True)
            else:
                raise

    async def _start_scan(self, query, user_id: int, context: ContextTypes.DEFAULT_TYPE):
        """Запустить сканирование"""
        settings = await self.db.get_user_settings(user_id)
        enabled_signals = settings.get('enabled_signals', []) if settings else []

        if not enabled_signals:
            await query.edit_message_text(
                "⚠️ Выберите хотя бы один тип сигнала!",
                reply_markup=self.keyboards.get_signal_types_keyboard([])
            )
            return

        await query.edit_message_text(
            "🚀 Запускаю сканирование...\n\nЭто может занять несколько минут.\n\n⚠️ Стейблкоины исключены из анализа.",
            reply_markup=self.keyboards.get_scan_control_keyboard(is_scanning=True)
        )

        # Запускаем сканирование в фоне
        asyncio.create_task(
            self._perform_scan(user_id, enabled_signals, query.message.chat_id, context)
        )

    async def _perform_scan(self, user_id: int, enabled_signals: List[str], chat_id: int,
                            context: ContextTypes.DEFAULT_TYPE):
        """Выполнить сканирование"""
        start_time = datetime.utcnow()

        try:
            settings = await self.db.get_user_settings(user_id)
            timeframe = settings.get('timeframe', DEFAULT_TIMEFRAME) if settings else DEFAULT_TIMEFRAME

            # Получаем топ монеты (без стейблкоинов)
            symbols = await self.binance.get_top_coins()

            total_signals = []
            processed = 0

            for symbol in symbols:
                try:
                    # Получаем данные
                    df = await self.binance.get_ohlcv(symbol, timeframe)
                    if df is None or len(df) < 20:
                        continue

                    # Добавляем индикаторы
                    df = self.processor.add_technical_indicators(df)

                    # Находим уровни
                    levels = self.processor.find_support_resistance(df)

                    # Генерируем сигналы
                    signals = await self.signal_generator.analyze_symbol(
                        df, symbol, levels, enabled_signals
                    )

                    if signals:
                        for signal in signals:
                            # Сохраняем в БД
                            await self.db.save_signal(user_id, signal)
                            total_signals.append(signal)

                    processed += 1

                    # Каждые 20 монет отправляем прогресс
                    if processed % 20 == 0:
                        await self._send_progress(context, chat_id, processed, len(symbols))

                except Exception as e:
                    logger.error(f"Ошибка анализа {symbol}: {e}")
                    continue

            # Вычисляем время сканирования
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()

            # Сохраняем историю сканирования
            await self.db.create_scan_history(
                user_id,
                processed,
                len(total_signals),
                timeframe,
                enabled_signals,
                duration
            )

            # Отправляем результаты
            await self._send_scan_results(context, chat_id, total_signals, processed)

        except Exception as e:
            logger.error(f"Ошибка сканирования: {e}")
            await self._send_error(context, chat_id, str(e))

    async def _send_progress(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, processed: int, total: int):
        """Отправить прогресс сканирования"""
        progress = (processed / total) * 100
        message = f"⏳ Прогресс: {processed}/{total} ({progress:.1f}%)"

        try:
            await context.bot.send_message(chat_id, message)
        except Exception as e:
            logger.error(f"Ошибка отправки прогресса: {e}")

    async def _send_scan_results(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, signals: List[Dict],
                                 processed: int):
        """Отправить результаты сканирования"""
        if not signals:
            message = f"✅ Сканирование завершено!\n\n📊 Проанализировано: {processed} монет\n⚠️ Сигналов не найдено."
            await context.bot.send_message(chat_id, message, parse_mode=ParseMode.HTML)
            return

        # Группируем по приоритету
        critical = [s for s in signals if s.get('priority') == 'critical']
        high = [s for s in signals if s.get('priority') == 'high']
        medium = [s for s in signals if s.get('priority') == 'medium']

        # Исключаем confluence из подсчета (они формируются из других сигналов)
        non_confluence = [s for s in signals if s.get('type') != 'confluence']

        message = f"""
✅ <b>Сканирование завершено!</b>

📊 Проанализировано: <code>{processed}</code> монет (без стейблкоинов)
🎯 Найдено сигналов: <code>{len(non_confluence)}</code>

⭐ Критические: <code>{len([s for s in critical if s.get('type') != 'confluence'])}</code>
🔴 Высокий приоритет: <code>{len(high)}</code>
🟡 Средний приоритет: <code>{len(medium)}</code>

<b>📬 Отправляю топ-10 разнообразных сигналов...</b>
        """

        await context.bot.send_message(chat_id, message, parse_mode=ParseMode.HTML)

        # НОВАЯ ЛОГИКА: Показываем разнообразные сигналы, НЕ confluence
        # Берем лучшие сигналы каждого типа
        signals_by_type = {}
        for signal in non_confluence:
            sig_type = signal.get('type')
            priority = signal.get('priority')

            if sig_type not in signals_by_type:
                signals_by_type[sig_type] = []

            signals_by_type[sig_type].append(signal)

        # Сортируем каждый тип по приоритету
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}

        top_signals = []
        for sig_type, sigs in signals_by_type.items():
            # Сортируем по приоритету
            sorted_sigs = sorted(sigs, key=lambda x: priority_order.get(x.get('priority', 'low'), 3))
            # Берем лучший сигнал этого типа
            if sorted_sigs:
                top_signals.append(sorted_sigs[0])

        # Сортируем все топ сигналы по приоритету
        top_signals = sorted(top_signals, key=lambda x: priority_order.get(x.get('priority', 'low'), 3))

        # Отправляем топ-10 разнообразных сигналов
        for i, signal in enumerate(top_signals[:10], 1):
            try:
                formatted = self.formatter.format_signal(signal)

                # Добавляем номер и общую информацию
                header = f"━━━━━━━━━━━━━━━━━\n<b>📊 Сигнал {i} из {min(10, len(top_signals))}</b>\n━━━━━━━━━━━━━━━━━\n\n"

                await context.bot.send_message(chat_id, header + formatted, parse_mode=ParseMode.HTML)
                await asyncio.sleep(0.7)
            except Exception as e:
                logger.error(f"Ошибка отправки сигнала: {e}")

        # Если сигналов больше 10, показываем сводку остальных
        if len(top_signals) > 10:
            summary = f"\n\n━━━━━━━━━━━━━━━━━\n<b>📋 Краткая сводка остальных сигналов</b>\n━━━━━━━━━━━━━━━━━\n\n"

            # Группируем по монетам
            remaining_signals = top_signals[10:]
            coins_summary = {}

            for sig in remaining_signals:
                symbol = sig.get('symbol')
                sig_type = sig.get('type')
                direction = sig.get('direction')

                if symbol not in coins_summary:
                    coins_summary[symbol] = []

                emoji = self._get_signal_emoji(sig_type)
                dir_emoji = '🟢' if direction == 'bullish' else '🔴' if direction == 'bearish' else '⚪'

                coins_summary[symbol].append(f"{emoji} {SIGNAL_TYPES.get(sig_type, sig_type)} {dir_emoji}")

            # Показываем топ-10 монет из остальных
            for symbol, sigs in list(coins_summary.items())[:10]:
                summary += f"<b>{symbol}</b>:\n"
                for sig_info in sigs[:3]:  # Максимум 3 сигнала на монету
                    summary += f"  • {sig_info}\n"
                summary += "\n"

            if len(coins_summary) > 10:
                summary += f"<i>... и еще {len(coins_summary) - 10} монет с сигналами</i>"

            await context.bot.send_message(chat_id, summary, parse_mode=ParseMode.HTML)

    async def _send_error(self, context: ContextTypes.DEFAULT_TYPE, chat_id: int, error: str):
        """Отправить сообщение об ошибке"""
        message = f"❌ Произошла ошибка при сканировании:\n\n<code>{error}</code>"
        try:
            await context.bot.send_message(chat_id, message, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения об ошибке: {e}")

    def _format_signal_types(self) -> str:
        """Форматировать список типов сигналов"""
        return "\n".join([f"• {name}" for name in SIGNAL_TYPES.values()])

    def _get_signal_emoji(self, signal_type: str) -> str:
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

    def _format_top_coins(self, top_coins: List[Dict]) -> str:
        """Форматировать топ монет"""
        if not top_coins:
            return "Нет данных"

        result = ""
        for i, coin in enumerate(top_coins[:5], 1):
            result += f"{i}. <code>{coin['symbol']}</code> - {coin['count']} сигналов\n"
        return result

    def _format_top_signal_types(self, top_types: List[Dict]) -> str:
        """Форматировать топ типов сигналов"""
        if not top_types:
            return "Нет данных"

        result = ""
        for signal_type in top_types[:5]:
            emoji = self._get_signal_emoji(signal_type['type'])
            result += f"{emoji} {SIGNAL_TYPES.get(signal_type['type'], signal_type['type'])} - {signal_type['count']}\n"
        return result

    async def _show_timeframe_settings(self, query, user_id: int):
        """Показать настройки таймфрейма"""
        settings = await self.db.get_user_settings(user_id)
        current_tf = settings.get('timeframe', DEFAULT_TIMEFRAME) if settings else DEFAULT_TIMEFRAME

        await query.edit_message_text(
            f"📊 <b>Выбор таймфрейма</b>\n\nТекущий: <code>{current_tf}</code>",
            reply_markup=self.keyboards.get_timeframe_keyboard(current_tf),
            parse_mode=ParseMode.HTML
        )

    async def _set_timeframe(self, query, user_id: int, timeframe: str):
        """Установить таймфрейм"""
        await self.db.update_user_settings(user_id, {'timeframe': timeframe})

        await query.edit_message_text(
            f"✅ Таймфрейм установлен: <code>{timeframe}</code>",
            reply_markup=self.keyboards.get_timeframe_keyboard(timeframe),
            parse_mode=ParseMode.HTML
        )
        await query.answer(f"✅ Таймфрейм изменен на {timeframe}")

    async def _show_signal_settings(self, query, user_id: int):
        """Показать настройки сигналов"""
        settings = await self.db.get_user_settings(user_id)
        enabled_signals = settings.get('enabled_signals', []) if settings else []

        await query.edit_message_text(
            "🎯 <b>Выбор типов сигналов</b>\n\nВыберите какие сигналы хотите отслеживать:",
            reply_markup=self.keyboards.get_signal_types_keyboard(enabled_signals),
            parse_mode=ParseMode.HTML
        )

    async def _show_notification_settings(self, query, user_id: int):
        """Показать настройки уведомлений"""
        settings = await self.db.get_user_settings(user_id)
        enabled = settings.get('notifications_enabled', True) if settings else True

        await query.edit_message_text(
            "🔔 <b>Настройки уведомлений</b>",
            reply_markup=self.keyboards.get_notifications_keyboard(enabled),
            parse_mode=ParseMode.HTML
        )

    async def _toggle_notifications(self, query, user_id: int):
        """Переключить уведомления"""
        settings = await self.db.get_user_settings(user_id)
        current = settings.get('notifications_enabled', True) if settings else True
        new_value = not current

        await self.db.update_user_settings(user_id, {'notifications_enabled': new_value})

        try:
            await query.edit_message_reply_markup(
                reply_markup=self.keyboards.get_notifications_keyboard(new_value)
            )
            status = "включены" if new_value else "выключены"
            await query.answer(f"🔔 Уведомления {status}")
        except BadRequest as e:
            if "message is not modified" in str(e).lower():
                await query.answer("Настройка уже установлена", show_alert=False)
            else:
                raise

    async def _show_settings_menu(self, query, user_id: int):
        """Показать меню настроек"""
        settings = await self.db.get_user_settings(user_id)

        timeframe = settings.get('timeframe', DEFAULT_TIMEFRAME) if settings else DEFAULT_TIMEFRAME
        notifications = settings.get('notifications_enabled', True) if settings else True
        notifications_text = 'Включены' if notifications else 'Выключены'
        min_volume = settings.get('min_volume', 1000000) if settings else 1000000

        message = f"""
⚙️ <b>Настройки</b>

Текущие параметры:
📊 Таймфрейм: <code>{timeframe}</code>
🔔 Уведомления: <code>{notifications_text}</code>
💰 Мин. объем: <code>${min_volume:,.0f}</code>

Выберите что хотите изменить:
        """

        await query.edit_message_text(
            message,
            reply_markup=self.keyboards.get_settings_keyboard(),
            parse_mode=ParseMode.HTML
        )

    async def _show_main_menu(self, query):
        """Показать главное меню"""
        await query.message.reply_text(
            "📱 Главное меню",
            reply_markup=self.keyboards.get_main_menu()
        )

    async def _stop_scan(self, query, user_id: int):
        """Остановить сканирование"""
        if user_id in self.active_scans:
            self.active_scans[user_id] = False

        await query.edit_message_text(
            "⏹ Сканирование остановлено.",
            reply_markup=self.keyboards.get_scan_control_keyboard(is_scanning=False)
        )
        await query.answer("Сканирование остановлено")