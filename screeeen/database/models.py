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