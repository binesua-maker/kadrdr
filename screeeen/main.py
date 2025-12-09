import asyncio
import sys
from loguru import logger
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from telegram.error import BadRequest, TimedOut, NetworkError

from config.api_keys import get_telegram_token
from config.settings import LOG_LEVEL, LOG_FILE, SCAN_INTERVAL
from database.db_manager import DatabaseManager
from bot.handlers import BotHandlers

# Настройка логирования
logger.remove()
logger.add(sys.stderr, level=LOG_LEVEL)
logger.add(LOG_FILE, rotation="10 MB", retention="7 days", level=LOG_LEVEL)


class CryptoScreenerBot:
    """Главный класс бота"""

    def __init__(self):
        self.token = get_telegram_token()
        self.db = DatabaseManager()
        self.handlers = BotHandlers(self.db)
        self.application = None
        self.background_scanner_task = None

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Глобальный обработчик ошибок"""
        try:
            logger.error(f"Exception while handling an update: {context.error}")

            # Игнорируем некоторые ошибки
            if isinstance(context.error, BadRequest):
                if "message is not modified" in str(context.error).lower():
                    logger.debug("Сообщение не изменилось - игнорируем")
                    return
                elif "message to edit not found" in str(context.error).lower():
                    logger.debug("Сообщение не найдено - игнорируем")
                    return

            if isinstance(context.error, (TimedOut, NetworkError)):
                logger.warning(f"Сетевая ошибка: {context.error}")
                return

            # Для других ошибок уведомляем пользователя
            if update and hasattr(update, 'effective_message'):
                try:
                    await update.effective_message.reply_text(
                        "❌ Произошла ошибка. Попробуйте еще раз или обратитесь к администратору."
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение об ошибке: {e}")

        except Exception as e:
            logger.error(f"Ошибка в обработчике ошибок: {e}")

    def setup_handlers(self):
        """Регистрация обработчиков команд"""
        app = self.application

        # Регистрируем обработчик ошибок
        app.add_error_handler(self.error_handler)

        # Команды
        app.add_handler(CommandHandler("start", self.handlers.start_command))
        app.add_handler(CommandHandler("help", self.handlers.help_command))
        app.add_handler(CommandHandler("scan", self.handlers.scan_command))
        app.add_handler(CommandHandler("settings", self.handlers.settings_command))
        app.add_handler(CommandHandler("history", self.handlers.history_command))
        app.add_handler(CommandHandler("stats", self.handlers.stats_command))

        # Callback кнопки
        app.add_handler(CallbackQueryHandler(self.handlers.button_callback))

        # Текстовые сообщения (для меню)
        app.add_handler(MessageHandler(
            filters.Regex("^🔍 Запустить скан$"),
            self.handlers.scan_command
        ))
        app.add_handler(MessageHandler(
            filters.Regex("^⚙️ Настройки$"),
            self.handlers.settings_command
        ))
        app.add_handler(MessageHandler(
            filters.Regex("^📊 История сигналов$"),
            self.handlers.history_command
        ))
        app.add_handler(MessageHandler(
            filters.Regex("^📈 Статистика$"),
            self.handlers.stats_command
        ))
        app.add_handler(MessageHandler(
            filters.Regex("^❓ Помощь$"),
            self.handlers.help_command
        ))
        app.add_handler(MessageHandler(
            filters.Regex("^ℹ️ О боте$"),
            self.about_handler
        ))

        logger.info("Обработчики команд зарегистрированы")

    async def about_handler(self, update: Update, context):
        """Информация о боте"""
        about_text = """
ℹ️ <b>О боте</b>

<b>Crypto Screener Bot v1.0</b>

Профессиональный инструмент для анализа криптовалютного рынка с использованием Smart Money Concepts и технического анализа.

<b>Возможности:</b>
• Мониторинг топ-100 монет Binance
• 11 типов технического анализа
• Smart Money Concepts (SMC)
• Order Blocks & FVG
• Дивергенции и паттерны
• Реал-тайм уведомления
• Автоматическое исключение стейблкоинов

<b>Исключаются из анализа:</b>
• USDT, USDC, BUSD, DAI и другие стейблкоины

<b>Технологии:</b>
• Python 3.11+
• python-telegram-bot
• CCXT (Binance API)
• pandas (Technical Analysis)
• SQLAlchemy (Database)

<b>Разработчик:</b> @binesua_maker
<b>Версия:</b> 1.0.0
<b>Дата:</b> 2025-01-11

⭐ Если бот полезен, поставьте звезду на GitHub!
        """
        await update.message.reply_text(about_text, parse_mode='HTML')

    async def post_init(self, application: Application):
        """Инициализация после запуска бота"""
        logger.info("Бот инициализирован и готов к работе")
        logger.info(f"Bot username: @{application.bot.username}")

        # Запускаем фоновый сканер (опционально)
        # self.background_scanner_task = asyncio.create_task(self.background_scanner())

    async def post_shutdown(self, application: Application):
        """Очистка при остановке бота"""
        logger.info("Остановка бота...")

        # Останавливаем фоновый сканер
        if self.background_scanner_task:
            self.background_scanner_task.cancel()
            try:
                await self.background_scanner_task
            except asyncio.CancelledError:
                pass

        logger.info("Бот остановлен")

    async def background_scanner(self):
        """Фоновое сканирование рынка"""
        logger.info("Запущен фоновый сканер")

        while True:
            try:
                logger.info("Начало фонового сканирования...")

                # Здесь можно добавить логику фонового сканирования
                # для всех пользователей с включенными уведомлениями

                await asyncio.sleep(SCAN_INTERVAL)

            except asyncio.CancelledError:
                logger.info("Фоновый сканер остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка фонового сканирования: {e}")
                await asyncio.sleep(60)

    def run(self):
        """Запуск бота"""
        try:
            logger.info("Запуск Crypto Screener Bot...")

            # Создаем приложение с правильной конфигурацией
            self.application = (
                Application.builder()
                .token(self.token)
                .post_init(self.post_init)
                .post_shutdown(self.post_shutdown)
                .concurrent_updates(True)
                .build()
            )

            # Регистрируем обработчики
            self.setup_handlers()

            # Запускаем бота
            logger.info("Бот успешно запущен! Нажмите Ctrl+C для остановки.")
            self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                close_loop=False
            )

        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки (Ctrl+C)")
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
        finally:
            logger.info("Завершение работы бота")


def main():
    """Точка входа"""
    try:
        bot = CryptoScreenerBot()
        bot.run()
    except Exception as e:
        logger.critical(f"Не удалось запустить бота: {e}")
        import traceback
        logger.critical(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()