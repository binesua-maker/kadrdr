from sqlalchemy import create_engine, func, desc
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional, List, Dict
from loguru import logger
from datetime import datetime, timedelta
import json
import numpy as np
import pandas as pd

from database.models import Base, User, UserSettings, Signal, ScanHistory
from config.settings import DATABASE_URL


class DatabaseManager:
    """Менеджер базы данных"""

    def __init__(self, db_url: str = DATABASE_URL):
        # Поддержка синхронной работы с SQLite
        self.engine = create_engine(db_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine, class_=Session)

        # Создаем таблицы
        Base.metadata.create_all(self.engine)
        logger.info("База данных инициализирована")

    def get_session(self) -> Session:
        """Получить сессию БД"""
        return self.SessionLocal()

    @staticmethod
    def _convert_to_serializable(obj):
        """Конвертировать numpy/pandas типы в JSON-сериализуемые"""
        if isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat() if hasattr(obj, 'isoformat') else str(obj)
        elif isinstance(obj, dict):
            return {key: DatabaseManager._convert_to_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [DatabaseManager._convert_to_serializable(item) for item in obj]
        elif isinstance(obj, bool):
            return bool(obj)
        elif obj is None:
            return None
        elif isinstance(obj, str):
            return str(obj)
        else:
            try:
                return float(obj)
            except (TypeError, ValueError):
                return str(obj)

    @staticmethod
    def _clean_signal_data(signal_data: Dict) -> Dict:
        """Очистить данные сигнала перед сохранением"""
        cleaned = {}

        # Основные поля
        cleaned['symbol'] = str(signal_data.get('symbol', ''))
        cleaned['signal_type'] = str(signal_data.get('type', ''))
        cleaned['direction'] = str(signal_data.get('direction', ''))
        cleaned['priority'] = str(signal_data.get('priority', 'medium'))

        # Числовые поля
        price = signal_data.get('price', 0)
        cleaned['price'] = float(price) if price and not pd.isna(price) else 0.0

        rsi = signal_data.get('rsi')
        if rsi is not None and not pd.isna(rsi):
            cleaned['rsi'] = float(rsi)
        else:
            cleaned['rsi'] = None

        macd = signal_data.get('macd')
        if macd is not None and not pd.isna(macd):
            cleaned['macd'] = float(macd)
        else:
            cleaned['macd'] = None

        strength = signal_data.get('strength_index')
        if strength is not None and not pd.isna(strength):
            cleaned['strength_index'] = float(strength)
        else:
            cleaned['strength_index'] = None

        # Тренд
        trend = signal_data.get('trend')
        if isinstance(trend, dict):
            cleaned['trend'] = str(trend.get('trend', 'unknown'))
        else:
            cleaned['trend'] = str(trend) if trend else None

        # Details - конвертируем все типы включая numpy bool
        details = signal_data.get('details', {})
        cleaned['details'] = DatabaseManager._convert_to_serializable(details)

        # Timestamp
        timestamp = signal_data.get('timestamp')
        if isinstance(timestamp, (pd.Timestamp, datetime)):
            cleaned['timestamp'] = timestamp.replace(tzinfo=None) if hasattr(timestamp,
                                                                             'replace') else datetime.utcnow()
        else:
            cleaned['timestamp'] = datetime.utcnow()

        return cleaned

    # === User operations ===

    async def create_user(self, telegram_id: int, username: str = None) -> User:
        """Создать пользователя"""
        session = self.get_session()
        try:
            # Проверяем существует ли пользователь
            user = session.query(User).filter(User.telegram_id == telegram_id).first()

            if user:
                # Обновляем last_active
                user.last_active = datetime.utcnow()
                if username:
                    user.username = username
            else:
                # Создаем нового пользователя
                user = User(telegram_id=telegram_id, username=username)
                session.add(user)
                session.flush()

                # Создаем настройки по умолчанию
                settings = UserSettings(user_id=user.id)
                session.add(settings)

            session.commit()
            session.refresh(user)
            return user

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка создания пользователя: {e}")
            raise
        finally:
            session.close()

    async def get_user(self, telegram_id: int) -> Optional[User]:
        """Получить пользователя"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            return user
        finally:
            session.close()

    # === Settings operations ===

    async def get_user_settings(self, telegram_id: int) -> Optional[Dict]:
        """Получить настройки пользователя"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user or not user.settings:
                return None

            settings = user.settings
            return {
                'timeframe': settings.timeframe,
                'enabled_signals': settings.enabled_signals or [],
                'notifications_enabled': settings.notifications_enabled,
                'min_volume': settings.min_volume,
                'min_price_change': settings.min_price_change
            }
        finally:
            session.close()

    async def update_user_settings(self, telegram_id: int, updates: Dict) -> bool:
        """Обновить настройки пользователя"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False

            if not user.settings:
                user.settings = UserSettings(user_id=user.id)

            # Обновляем настройки
            for key, value in updates.items():
                if hasattr(user.settings, key):
                    setattr(user.settings, key, value)

            session.commit()
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка обновления настроек: {e}")
            return False
        finally:
            session.close()

    # === Signal operations ===

    async def save_signal(self, telegram_id: int, signal_data: Dict) -> Optional[Signal]:
        """Сохранить сигнал"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                logger.warning(f"Пользователь {telegram_id} не найден")
                return None

            # Очищаем данные
            cleaned_data = self._clean_signal_data(signal_data)

            signal = Signal(
                user_id=user.id,
                symbol=cleaned_data['symbol'],
                signal_type=cleaned_data['signal_type'],
                direction=cleaned_data['direction'],
                priority=cleaned_data['priority'],
                price=cleaned_data['price'],
                details=cleaned_data['details'],
                rsi=cleaned_data['rsi'],
                macd=cleaned_data['macd'],
                trend=cleaned_data['trend'],
                strength_index=cleaned_data['strength_index'],
                timestamp=cleaned_data['timestamp']
            )

            session.add(signal)
            session.commit()
            session.refresh(signal)
            return signal

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка сохранения сигнала: {e}")
            return None
        finally:
            session.close()

    async def get_user_signals(self, telegram_id: int, limit: int = 50) -> List[Dict]:
        """Получить сигналы пользователя"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return []

            signals = session.query(Signal).filter(
                Signal.user_id == user.id
            ).order_by(desc(Signal.timestamp)).limit(limit).all()

            return [
                {
                    'id': s.id,
                    'symbol': s.symbol,
                    'type': s.signal_type,
                    'direction': s.direction,
                    'priority': s.priority,
                    'price': s.price,
                    'details': s.details,
                    'rsi': s.rsi,
                    'macd': s.macd,
                    'trend': s.trend,
                    'strength_index': s.strength_index,
                    'timestamp': s.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                for s in signals
            ]
        finally:
            session.close()

    async def get_user_statistics(self, telegram_id: int) -> Dict:
        """Получить статистику пользователя"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return {}

            # Общее количество сигналов
            total_signals = session.query(func.count(Signal.id)).filter(
                Signal.user_id == user.id
            ).scalar()

            # Бычьи сигналы
            bullish_signals = session.query(func.count(Signal.id)).filter(
                Signal.user_id == user.id,
                Signal.direction == 'bullish'
            ).scalar()

            # Медвежьи сигналы
            bearish_signals = session.query(func.count(Signal.id)).filter(
                Signal.user_id == user.id,
                Signal.direction == 'bearish'
            ).scalar()

            # Топ монет
            top_coins = session.query(
                Signal.symbol,
                func.count(Signal.id).label('count')
            ).filter(
                Signal.user_id == user.id
            ).group_by(Signal.symbol).order_by(desc('count')).limit(5).all()

            # Топ типов сигналов
            top_signal_types = session.query(
                Signal.signal_type,
                func.count(Signal.id).label('count')
            ).filter(
                Signal.user_id == user.id
            ).group_by(Signal.signal_type).order_by(desc('count')).limit(5).all()

            # Последнее сканирование
            last_scan = session.query(ScanHistory).filter(
                ScanHistory.user_id == user.id
            ).order_by(desc(ScanHistory.timestamp)).first()

            return {
                'total_signals': total_signals or 0,
                'bullish_signals': bullish_signals or 0,
                'bearish_signals': bearish_signals or 0,
                'top_coins': [{'symbol': c.symbol, 'count': c.count} for c in top_coins],
                'top_signal_types': [{'type': t.signal_type, 'count': t.count} for t in top_signal_types],
                'last_scan': last_scan.timestamp.strftime('%Y-%m-%d %H:%M:%S') if last_scan else 'Никогда'
            }
        finally:
            session.close()

    # === Scan History operations ===

    async def create_scan_history(
            self,
            telegram_id: int,
            coins_scanned: int,
            signals_found: int,
            timeframe: str = None,
            enabled_signal_types: List[str] = None,
            duration_seconds: float = None
    ) -> Optional[ScanHistory]:
        """Создать запись истории сканирования"""
        session = self.get_session()
        try:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return None

            scan = ScanHistory(
                user_id=user.id,
                coins_scanned=coins_scanned,
                signals_found=signals_found,
                timeframe=timeframe,
                enabled_signal_types=enabled_signal_types,
                duration_seconds=duration_seconds,
                status='completed'
            )

            session.add(scan)
            session.commit()
            session.refresh(scan)
            return scan

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка создания истории сканирования: {e}")
            return None
        finally:
            session.close()

    async def cleanup_old_signals(self, days: int = 30):
        """Удалить старые сигналы"""
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted = session.query(Signal).filter(
                Signal.timestamp < cutoff_date
            ).delete()

            session.commit()
            logger.info(f"Удалено {deleted} старых сигналов")

        except Exception as e:
            session.rollback()
            logger.error(f"Ошибка очистки старых сигналов: {e}")
        finally:
            session.close()