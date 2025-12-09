from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    """Модель пользователя"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    signals = relationship("Signal", back_populates="user", cascade="all, delete-orphan")
    scan_history = relationship("ScanHistory", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username='{self.username}')>"


class UserSettings(Base):
    """Настройки пользователя"""
    __tablename__ = 'user_settings'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    
    timeframe = Column(String(10), default='15m')
    enabled_signals = Column(JSON, default=list)  # Список включенных типов сигналов
    notifications_enabled = Column(Boolean, default=True)
    min_volume = Column(Float, default=1000000.0)
    min_price_change = Column(Float, default=2.0)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="settings")
    
    def __repr__(self):
        return f"<UserSettings(user_id={self.user_id}, timeframe='{self.timeframe}')>"


class Signal(Base):
    """Торговый сигнал"""
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False, index=True)  # structure_break, level_approach, etc.
    direction = Column(String(20), nullable=False)  # bullish, bearish, neutral
    priority = Column(String(20), default='medium')  # critical, high, medium, low
    
    price = Column(Float, nullable=False)
    details = Column(JSON, nullable=True)  # Детали сигнала
    
    # Технические данные
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    trend = Column(String(20), nullable=True)
    strength_index = Column(Float, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="signals")
    
    def __repr__(self):
        return f"<Signal(symbol='{self.symbol}', type='{self.signal_type}', direction='{self.direction}')>"


class ScanHistory(Base):
    """История сканирований"""
    __tablename__ = 'scan_history'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    coins_scanned = Column(Integer, default=0)
    signals_found = Column(Integer, default=0)
    timeframe = Column(String(10), nullable=True)
    enabled_signal_types = Column(JSON, nullable=True)
    
    duration_seconds = Column(Float, nullable=True)
    status = Column(String(20), default='completed')  # completed, failed, cancelled
    error_message = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="scan_history")
    
    def __repr__(self):
        return f"<ScanHistory(user_id={self.user_id}, coins_scanned={self.coins_scanned}, signals={self.signals_found})>"


class Subscription(Base):
    """Подписки пользователя на монеты"""
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<Subscription(user_id={self.user_id}, symbol='{self.symbol}')>"


class PriceAlert(Base):
    """Ценовые алерты"""
    __tablename__ = 'price_alerts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    target_price = Column(Float, nullable=False)
    condition = Column(String(10), nullable=False)  # 'above' or 'below'
    status = Column(String(20), default='active')  # active, triggered, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    triggered_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<PriceAlert(symbol='{self.symbol}', price={self.target_price}, condition='{self.condition}')>"


class Position(Base):
    """Торговые позиции портфеля"""
    __tablename__ = 'positions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    side = Column(String(10), nullable=False)  # 'long' or 'short'
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    status = Column(String(20), default='open')  # open, closed
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    close_price = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<Position(symbol='{self.symbol}', side='{self.side}', entry={self.entry_price})>"


class ScanSchedule(Base):
    """Расписание автоматических сканирований"""
    __tablename__ = 'scan_schedules'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    interval_minutes = Column(Integer, nullable=False)
    timeframe = Column(String(10), nullable=False)
    enabled = Column(Boolean, default=True)
    last_run = Column(DateTime, nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    
    def __repr__(self):
        return f"<ScanSchedule(user_id={self.user_id}, interval={self.interval_minutes}m, enabled={self.enabled})>"


class SignalPerformance(Base):
    """Статистика эффективности сигналов"""
    __tablename__ = 'signal_performance'
    
    id = Column(Integer, primary_key=True)
    signal_id = Column(Integer, ForeignKey('signals.id'), nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    signal_type = Column(String(50), nullable=False)
    entry_price = Column(Float, nullable=False)
    
    # Результаты через разные промежутки времени
    price_after_1h = Column(Float, nullable=True)
    price_after_4h = Column(Float, nullable=True)
    price_after_24h = Column(Float, nullable=True)
    
    change_1h = Column(Float, nullable=True)
    change_4h = Column(Float, nullable=True)
    change_24h = Column(Float, nullable=True)
    
    outcome = Column(String(20), nullable=True)  # 'success', 'failed', 'pending'
    checked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    signal = relationship("Signal", foreign_keys=[signal_id])
    
    def __repr__(self):
        return f"<SignalPerformance(symbol='{self.symbol}', type='{self.signal_type}', outcome='{self.outcome}')>"