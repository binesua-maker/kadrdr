"""
Portfolio Management - Управление портфелем позиций
"""
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from database.models import Position, User
from data.binance_client import BinanceDataClient


class PortfolioManager:
    """Менеджер портфеля позиций"""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.binance = BinanceDataClient()
    
    async def add_position(
        self,
        user_id: int,
        symbol: str,
        entry_price: float,
        quantity: float,
        side: str = 'long',
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict:
        """
        Добавить новую позицию в портфель
        
        Args:
            user_id: ID пользователя в Telegram
            symbol: Символ монеты
            entry_price: Цена входа
            quantity: Количество
            side: Направление ('long' или 'short')
            stop_loss: Stop Loss (опционально)
            take_profit: Take Profit (опционально)
        
        Returns:
            Информация о добавленной позиции
        """
        try:
            session = self.db.get_session()
            
            # Проверяем пользователя
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                session.close()
                return {'error': 'Пользователь не найден'}
            
            # Создаем позицию
            position = Position(
                user_id=user.id,
                symbol=symbol,
                entry_price=entry_price,
                quantity=quantity,
                side=side,
                stop_loss=stop_loss,
                take_profit=take_profit,
                status='open'
            )
            
            session.add(position)
            session.commit()
            
            position_id = position.id
            session.close()
            
            logger.info(f"Добавлена позиция #{position_id} для пользователя {user_id}: {side} {quantity} {symbol} @ {entry_price}")
            
            return {
                'id': position_id,
                'symbol': symbol,
                'entry_price': entry_price,
                'quantity': quantity,
                'side': side,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'status': 'open'
            }
            
        except Exception as e:
            logger.error(f"Ошибка добавления позиции: {e}")
            return {'error': str(e)}
    
    async def get_portfolio(self, user_id: int, open_only: bool = True) -> List[Dict]:
        """
        Получить портфель пользователя с расчетом P&L
        
        Args:
            user_id: ID пользователя
            open_only: Только открытые позиции
        
        Returns:
            Список позиций с P&L
        """
        try:
            session = self.db.get_session()
            
            # Получаем пользователя
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                session.close()
                return []
            
            # Запрос позиций
            query = session.query(Position).filter_by(user_id=user.id)
            
            if open_only:
                query = query.filter_by(status='open')
            
            positions = query.order_by(Position.created_at.desc()).all()
            
            result = []
            total_pnl = 0
            
            for position in positions:
                # Получаем текущую цену
                current_price = await self._get_current_price(position.symbol)
                
                # Рассчитываем P&L
                pnl_data = self._calculate_pnl(
                    entry_price=position.entry_price,
                    current_price=current_price,
                    quantity=position.quantity,
                    side=position.side
                )
                
                position_data = {
                    'id': position.id,
                    'symbol': position.symbol,
                    'entry_price': position.entry_price,
                    'current_price': current_price,
                    'quantity': position.quantity,
                    'side': position.side,
                    'stop_loss': position.stop_loss,
                    'take_profit': position.take_profit,
                    'status': position.status,
                    'pnl': pnl_data['pnl'],
                    'pnl_percent': pnl_data['pnl_percent'],
                    'created_at': position.created_at.isoformat() if position.created_at else None
                }
                
                result.append(position_data)
                
                if position.status == 'open':
                    total_pnl += pnl_data['pnl']
            
            session.close()
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка получения портфеля: {e}")
            return []
    
    async def _get_current_price(self, symbol: str) -> float:
        """Получить текущую цену символа"""
        try:
            ticker = await self.binance.get_ticker(symbol)
            if ticker and 'last' in ticker:
                return float(ticker['last'])
            return 0.0
        except Exception as e:
            logger.error(f"Ошибка получения цены для {symbol}: {e}")
            return 0.0
    
    def _calculate_pnl(
        self,
        entry_price: float,
        current_price: float,
        quantity: float,
        side: str
    ) -> Dict:
        """
        Рассчитать P&L позиции
        
        Args:
            entry_price: Цена входа
            current_price: Текущая цена
            quantity: Количество
            side: Направление
        
        Returns:
            P&L в USD и процентах
        """
        if current_price == 0:
            return {'pnl': 0, 'pnl_percent': 0}
        
        if side == 'long':
            # Long: профит когда цена растет
            pnl = (current_price - entry_price) * quantity
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
        else:  # short
            # Short: профит когда цена падает
            pnl = (entry_price - current_price) * quantity
            pnl_percent = ((entry_price - current_price) / entry_price) * 100
        
        return {
            'pnl': round(pnl, 2),
            'pnl_percent': round(pnl_percent, 2)
        }
    
    async def close_position(self, user_id: int, position_id: int, close_price: Optional[float] = None) -> bool:
        """
        Закрыть позицию
        
        Args:
            user_id: ID пользователя
            position_id: ID позиции
            close_price: Цена закрытия (если не указана, берется текущая)
        
        Returns:
            True если закрыто успешно
        """
        try:
            session = self.db.get_session()
            
            # Получаем пользователя
            user = session.query(User).filter_by(telegram_id=user_id).first()
            if not user:
                session.close()
                return False
            
            # Находим позицию
            position = session.query(Position).filter_by(
                id=position_id,
                user_id=user.id,
                status='open'
            ).first()
            
            if not position:
                session.close()
                return False
            
            # Получаем цену закрытия
            if close_price is None:
                close_price = await self._get_current_price(position.symbol)
            
            # Рассчитываем финальный P&L
            pnl_data = self._calculate_pnl(
                entry_price=position.entry_price,
                current_price=close_price,
                quantity=position.quantity,
                side=position.side
            )
            
            # Обновляем позицию
            position.status = 'closed'
            position.closed_at = datetime.utcnow()
            position.close_price = close_price
            position.pnl = pnl_data['pnl']
            
            session.commit()
            session.close()
            
            logger.info(f"Закрыта позиция #{position_id} с P&L: ${pnl_data['pnl']:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка закрытия позиции: {e}")
            return False
    
    def remove_position(self, user_id: int, position_id: int) -> bool:
        """
        Удалить позицию из портфеля
        
        Args:
            user_id: ID пользователя
            position_id: ID позиции
        
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
            
            # Находим и удаляем позицию
            position = session.query(Position).filter_by(
                id=position_id,
                user_id=user.id
            ).first()
            
            if position:
                session.delete(position)
                session.commit()
                session.close()
                logger.info(f"Удалена позиция #{position_id} пользователя {user_id}")
                return True
            else:
                session.close()
                return False
                
        except Exception as e:
            logger.error(f"Ошибка удаления позиции: {e}")
            return False
    
    async def get_total_pnl(self, user_id: int) -> Dict:
        """
        Получить общий P&L портфеля
        
        Args:
            user_id: ID пользователя
        
        Returns:
            Общий P&L и статистика
        """
        positions = await self.get_portfolio(user_id, open_only=True)
        
        total_pnl = sum(p['pnl'] for p in positions)
        total_investment = sum(p['entry_price'] * p['quantity'] for p in positions)
        
        avg_pnl_percent = (total_pnl / total_investment * 100) if total_investment > 0 else 0
        
        winning_positions = len([p for p in positions if p['pnl'] > 0])
        losing_positions = len([p for p in positions if p['pnl'] < 0])
        
        return {
            'total_pnl': round(total_pnl, 2),
            'avg_pnl_percent': round(avg_pnl_percent, 2),
            'total_positions': len(positions),
            'winning_positions': winning_positions,
            'losing_positions': losing_positions,
            'total_investment': round(total_investment, 2)
        }
    
    def format_portfolio(self, positions: List[Dict]) -> str:
        """Форматировать портфель для отображения"""
        if not positions:
            return "📭 Ваш портфель пуст"
        
        text = f"💼 <b>Ваш портфель ({len(positions)} позиций):</b>\n\n"
        
        total_pnl = 0
        
        for i, pos in enumerate(positions, 1):
            side_emoji = '🟢' if pos['side'] == 'long' else '🔴'
            pnl_emoji = '💰' if pos['pnl'] >= 0 else '💸'
            
            text += f"{i}. {side_emoji} <b>{pos['symbol']}</b> ({pos['side'].upper()})\n"
            text += f"   Вход: ${pos['entry_price']:,.2f} | Текущая: ${pos['current_price']:,.2f}\n"
            text += f"   Количество: {pos['quantity']}\n"
            text += f"   {pnl_emoji} P&L: ${pos['pnl']:+,.2f} ({pos['pnl_percent']:+.2f}%)\n"
            
            if pos.get('stop_loss'):
                text += f"   🛑 SL: ${pos['stop_loss']:,.2f}\n"
            if pos.get('take_profit'):
                text += f"   🎯 TP: ${pos['take_profit']:,.2f}\n"
            
            text += f"   ID: <code>{pos['id']}</code>\n\n"
            
            total_pnl += pos['pnl']
        
        # Итого
        total_emoji = '💰' if total_pnl >= 0 else '💸'
        text += f"\n{total_emoji} <b>Общий P&L: ${total_pnl:+,.2f}</b>\n"
        text += "\n<i>Используйте /remove [ID] для удаления позиции</i>"
        
        return text
    
    def format_pnl_summary(self, pnl_data: Dict) -> str:
        """Форматировать сводку P&L"""
        total_pnl = pnl_data['total_pnl']
        pnl_emoji = '💰' if total_pnl >= 0 else '💸'
        
        text = f"📊 <b>Сводка P&L</b>\n\n"
        text += f"{pnl_emoji} <b>Общий P&L:</b> ${total_pnl:+,.2f}\n"
        text += f"📈 <b>Средний P&L:</b> {pnl_data['avg_pnl_percent']:+.2f}%\n"
        text += f"💵 <b>Инвестировано:</b> ${pnl_data['total_investment']:,.2f}\n\n"
        
        text += f"<b>Позиции:</b>\n"
        text += f"  • Всего: {pnl_data['total_positions']}\n"
        text += f"  • 🟢 В плюсе: {pnl_data['winning_positions']}\n"
        text += f"  • 🔴 В минусе: {pnl_data['losing_positions']}\n"
        
        return text
