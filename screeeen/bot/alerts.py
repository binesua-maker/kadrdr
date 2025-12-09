"""
Price Alerts - Ценовые алерты
"""
import asyncio
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
from sqlalchemy.orm import Session

from database.models import PriceAlert, User
from data.binance_client import BinanceDataClient


class AlertManager:
    """Менеджер ценовых алертов"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.binance = BinanceDataClient()
        self.check_task = None
        self.running = False
    
    async def create_alert(
        self,
        user_id: int,
        symbol: str,
        target_price: float,
        condition: str
    ) -> Dict:
        """
        Создать новый ценовой алерт
        
        Args:
            user_id: ID пользователя в Telegram
            symbol: Символ монеты
            target_price: Целевая цена
            condition: Условие ('above' или 'below')
        
        Returns:
            Информация о созданном алерте
        """
        try:
            session = self.db.get_session()
            
            # Проверяем пользователя
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                session.close()
                return {'error': 'Пользователь не найден'}
            
            # Создаем алерт
            alert = PriceAlert(
                user_id=user.id,
                symbol=symbol,
                target_price=target_price,
                condition=condition,
                status='active'
            )
            
            session.add(alert)
            session.commit()
            
            alert_id = alert.id
            session.close()
            
            logger.info(f"Создан алерт #{alert_id} для пользователя {user_id}: {symbol} {condition} {target_price}")
            
            return {
                'id': alert_id,
                'symbol': symbol,
                'target_price': target_price,
                'condition': condition,
                'status': 'active'
            }
            
        except Exception as e:
            logger.error(f"Ошибка создания алерта: {e}")
            return {'error': str(e)}
    
    def get_user_alerts(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """
        Получить алерты пользователя
        
        Args:
            user_id: ID пользователя в Telegram
            active_only: Только активные алерты
        
        Returns:
            Список алертов
        """
        try:
            session = self.db.get_session()
            
            # Получаем пользователя
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                session.close()
                return []
            
            # Запрос алертов
            query = session.query(PriceAlert).filter_by(user_id=user.id)
            
            if active_only:
                query = query.filter_by(status='active')
            
            alerts = query.order_by(PriceAlert.created_at.desc()).all()
            
            result = []
            for alert in alerts:
                result.append({
                    'id': alert.id,
                    'symbol': alert.symbol,
                    'target_price': alert.target_price,
                    'condition': alert.condition,
                    'status': alert.status,
                    'created_at': alert.created_at.isoformat() if alert.created_at else None,
                    'triggered_at': alert.triggered_at.isoformat() if alert.triggered_at else None
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения алертов: {e}")
            return []
    
    def delete_alert(self, user_id: int, alert_id: int) -> bool:
        """
        Удалить алерт
        
        Args:
            user_id: ID пользователя
            alert_id: ID алерта
        
        Returns:
            True если удалено успешно
        """
        try:
            session = self.db.get_session()
            
            # Получаем пользователя
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                session.close()
                return False
            
            # Находим и удаляем алерт
            alert = session.query(PriceAlert).filter_by(
                id=alert_id,
                user_id=user.id
            ).first()
            
            if alert:
                session.delete(alert)
                session.commit()
                session.close()
                logger.info(f"Удален алерт #{alert_id} пользователя {user_id}")
                return True
            else:
                session.close()
                return False
                
        except Exception as e:
            logger.error(f"Ошибка удаления алерта: {e}")
            return False
    
    async def check_alerts(self) -> List[Dict]:
        """
        Проверить все активные алерты
        
        Returns:
            Список сработавших алертов
        """
        try:
            session = self.db.get_session()
            
            # Получаем все активные алерты
            active_alerts = session.query(PriceAlert).filter_by(status='active').all()
            
            if not active_alerts:
                session.close()
                return []
            
            triggered = []
            
            # Группируем алерты по символам для оптимизации
            alerts_by_symbol = {}
            for alert in active_alerts:
                if alert.symbol not in alerts_by_symbol:
                    alerts_by_symbol[alert.symbol] = []
                alerts_by_symbol[alert.symbol].append(alert)
            
            # Проверяем каждый символ
            for symbol, alerts in alerts_by_symbol.items():
                try:
                    # Получаем текущую цену
                    ticker = await self.binance.get_ticker(symbol)
                    if not ticker or 'last' not in ticker:
                        continue
                    
                    current_price = float(ticker['last'])
                    
                    # Проверяем каждый алерт
                    for alert in alerts:
                        if self._check_condition(current_price, alert.target_price, alert.condition):
                            # Алерт сработал!
                            alert.status = 'triggered'
                            alert.triggered_at = datetime.utcnow()
                            
                            # Получаем информацию о пользователе
                            user = session.query(User).filter_by(id=alert.user_id).first()
                            
                            triggered.append({
                                'alert_id': alert.id,
                                'user_id': user.telegram_id if user else None,
                                'symbol': alert.symbol,
                                'target_price': alert.target_price,
                                'current_price': current_price,
                                'condition': alert.condition
                            })
                            
                            logger.info(f"Сработал алерт #{alert.id}: {symbol} {current_price} {alert.condition} {alert.target_price}")
                    
                except Exception as e:
                    logger.error(f"Ошибка проверки алертов для {symbol}: {e}")
                    continue
            
            # Сохраняем изменения
            session.commit()
            session.close()
            
            return triggered
            
        except Exception as e:
            logger.error(f"Ошибка проверки алертов: {e}")
            return []
    
    def _check_condition(self, current_price: float, target_price: float, condition: str) -> bool:
        """Проверить условие срабатывания алерта"""
        if condition == 'above':
            return current_price >= target_price
        elif condition == 'below':
            return current_price <= target_price
        return False
    
    async def start_monitoring(self, bot_application, interval: int = 10):
        """
        Запустить фоновый мониторинг алертов
        
        Args:
            bot_application: Telegram bot application для отправки уведомлений
            interval: Интервал проверки в секундах
        """
        self.running = True
        logger.info(f"Запущен мониторинг алертов (интервал: {interval}s)")
        
        while self.running:
            try:
                # Проверяем алерты
                triggered_alerts = await self.check_alerts()
                
                # Отправляем уведомления
                for alert_data in triggered_alerts:
                    await self._send_alert_notification(bot_application, alert_data)
                
                # Ждем следующей проверки
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                logger.info("Мониторинг алертов остановлен")
                break
            except Exception as e:
                logger.error(f"Ошибка в мониторинге алертов: {e}")
                await asyncio.sleep(interval)
    
    async def _send_alert_notification(self, bot_application, alert_data: Dict):
        """Отправить уведомление о срабатывании алерта"""
        try:
            user_id = alert_data.get('user_id')
            if not user_id:
                return
            
            symbol = alert_data.get('symbol')
            target_price = alert_data.get('target_price')
            current_price = alert_data.get('current_price')
            condition = alert_data.get('condition')
            
            # Форматируем сообщение
            condition_text = 'выше' if condition == 'above' else 'ниже'
            
            message = f"""
🔔 <b>АЛЕРТ СРАБОТАЛ!</b>

💰 <b>{symbol}</b>
Цена {condition_text} целевой!

🎯 Целевая цена: ${target_price:,.2f}
💵 Текущая цена: ${current_price:,.2f}
📊 Изменение: {((current_price - target_price) / target_price * 100):+.2f}%

⏰ {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            """
            
            await bot_application.bot.send_message(
                chat_id=user_id,
                text=message.strip(),
                parse_mode='HTML'
            )
            
            logger.info(f"Отправлено уведомление об алерте пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об алерте: {e}")
    
    def stop_monitoring(self):
        """Остановить мониторинг"""
        self.running = False
        logger.info("Остановка мониторинга алертов...")
    
    def format_alerts_list(self, alerts: List[Dict]) -> str:
        """Форматировать список алертов для отображения"""
        if not alerts:
            return "📭 У вас нет активных алертов"
        
        text = f"🔔 <b>Ваши алерты ({len(alerts)}):</b>\n\n"
        
        for i, alert in enumerate(alerts, 1):
            condition_emoji = '⬆️' if alert['condition'] == 'above' else '⬇️'
            status_emoji = '✅' if alert['status'] == 'active' else '🔕'
            
            text += f"{i}. {status_emoji} {condition_emoji} <b>{alert['symbol']}</b>\n"
            text += f"   Цена {alert['condition']}: ${alert['target_price']:,.2f}\n"
            text += f"   ID: <code>{alert['id']}</code>\n\n"
        
        text += "\n<i>Используйте /delalert [ID] для удаления</i>"
        
        return text
