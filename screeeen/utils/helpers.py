from typing import Union, List
from datetime import datetime, timedelta
import pytz

class Helpers:
    """Вспомогательные функции"""
    
    @staticmethod
    def format_number(number: Union[int, float], decimals: int = 2) -> str:
        """Форматировать число с разделителями"""
        if number >= 1_000_000_000:
            return f"{number / 1_000_000_000:.{decimals}f}B"
        elif number >= 1_000_000:
            return f"{number / 1_000_000:.{decimals}f}M"
        elif number >= 1_000:
            return f"{number / 1_000:.{decimals}f}K"
        else:
            return f"{number:.{decimals}f}"
    
    @staticmethod
    def format_percentage(value: float, decimals: int = 2, show_sign: bool = True) -> str:
        """Форматировать процент"""
        sign = "+" if value > 0 and show_sign else ""
        return f"{sign}{value:.{decimals}f}%"
    
    @staticmethod
    def format_price(price: float, decimals: int = 4) -> str:
        """Форматировать цену"""
        if price >= 1000:
            return f"${price:,.2f}"
        elif price >= 1:
            return f"${price:.4f}"
        else:
            return f"${price:.8f}"
    
    @staticmethod
    def timeframe_to_minutes(timeframe: str) -> int:
        """Конвертировать таймфрейм в минуты"""
        mapping = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440,
            '1w': 10080
        }
        return mapping.get(timeframe.lower(), 15)
    
    @staticmethod
    def minutes_to_timeframe(minutes: int) -> str:
        """Конвертировать минуты в таймфрейм"""
        if minutes < 60:
            return f"{minutes}m"
        elif minutes < 1440:
            return f"{minutes // 60}h"
        elif minutes < 10080:
            return f"{minutes // 1440}d"
        else:
            return f"{minutes // 10080}w"
    
    @staticmethod
    def validate_timeframe(timeframe: str) -> bool:
        """Проверить валидность таймфрейма"""
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']
        return timeframe.lower() in valid_timeframes
    
    @staticmethod
    def get_utc_timestamp() -> datetime:
        """Получить текущее UTC время"""
        return datetime.now(pytz.UTC)
    
    @staticmethod
    def format_timestamp(timestamp: datetime, format: str = '%Y-%m-%d %H:%M:%S') -> str:
        """Форматировать timestamp"""
        return timestamp.strftime(format)
    
    @staticmethod
    def time_ago(timestamp: datetime) -> str:
        """Получить относительное время (например, '2 часа назад')"""
        now = datetime.now(pytz.UTC)
        if timestamp.tzinfo is None:
            timestamp = pytz.UTC.localize(timestamp)
        
        diff = now - timestamp
        
        if diff.days > 0:
            if diff.days == 1:
                return "1 день назад"
            elif diff.days < 7:
                return f"{diff.days} дня(ей) назад"
            elif diff.days < 30:
                weeks = diff.days // 7
                return f"{weeks} недель(и) назад"
            else:
                months = diff.days // 30
                return f"{months} месяц(ев) назад"
        
        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours} час(ов) назад"
        
        minutes = diff.seconds // 60
        if minutes > 0:
            return f"{minutes} минут(ы) назад"
        
        return "только что"
    
    @staticmethod
    def calculate_percentage_change(old_value: float, new_value: float) -> float:
        """Рассчитать процентное изменение"""
        if old_value == 0:
            return 0
        return ((new_value - old_value) / old_value) * 100
    
    @staticmethod
    def safe_divide(numerator: float, denominator: float, default: float = 0) -> float:
        """Безопасное деление"""
        if denominator == 0:
            return default
        return numerator / denominator
    
    @staticmethod
    def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Обрезать строку до определенной длины"""
        if len(text) <= max_length:
            return text
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def chunk_list(lst: List, chunk_size: int) -> List[List]:
        """Разбить список на чанки"""
        return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
    
    @staticmethod
    def sanitize_symbol(symbol: str) -> str:
        """Очистить название символа"""
        return symbol.replace('/', '').replace('-', '').upper()