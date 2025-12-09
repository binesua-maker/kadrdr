"""
Rate Limiter для защиты от превышения лимитов API
"""
import time
from collections import defaultdict
from typing import Dict, Optional
from loguru import logger
import asyncio


class RateLimiter:
    """Rate limiter для контроля частоты запросов к API"""
    
    def __init__(self, calls_per_minute: int = 1200, calls_per_second: int = 20):
        """
        Args:
            calls_per_minute: Максимум запросов в минуту
            calls_per_second: Максимум запросов в секунду
        """
        self.calls_per_minute = calls_per_minute
        self.calls_per_second = calls_per_second
        
        # История запросов
        self.minute_history: Dict[str, list] = defaultdict(list)
        self.second_history: Dict[str, list] = defaultdict(list)
        
        # Блокировки для синхронизации
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
    
    async def acquire(self, key: str = "default") -> None:
        """
        Получить разрешение на выполнение запроса
        Ждет, если достигнут лимит
        
        Args:
            key: Ключ для отдельного rate limiting (например, для разных API)
        """
        async with self.locks[key]:
            current_time = time.time()
            
            # Очищаем старые записи
            self._cleanup_history(key, current_time)
            
            # Проверяем лимиты
            while not self._can_proceed(key, current_time):
                wait_time = self._calculate_wait_time(key, current_time)
                if wait_time > 0:
                    logger.debug(f"Rate limit достигнут для '{key}', ожидание {wait_time:.2f}s")
                    await asyncio.sleep(wait_time)
                    current_time = time.time()
                    self._cleanup_history(key, current_time)
            
            # Добавляем текущий запрос в историю
            self.minute_history[key].append(current_time)
            self.second_history[key].append(current_time)
    
    def _cleanup_history(self, key: str, current_time: float) -> None:
        """Удалить старые записи из истории"""
        # Удаляем записи старше минуты
        self.minute_history[key] = [
            t for t in self.minute_history[key]
            if current_time - t < 60
        ]
        
        # Удаляем записи старше секунды
        self.second_history[key] = [
            t for t in self.second_history[key]
            if current_time - t < 1
        ]
    
    def _can_proceed(self, key: str, current_time: float) -> bool:
        """Проверить, можно ли выполнить запрос"""
        # Проверка лимита в минуту
        minute_count = len(self.minute_history[key])
        if minute_count >= self.calls_per_minute:
            return False
        
        # Проверка лимита в секунду
        second_count = len(self.second_history[key])
        if second_count >= self.calls_per_second:
            return False
        
        return True
    
    def _calculate_wait_time(self, key: str, current_time: float) -> float:
        """Рассчитать время ожидания"""
        wait_times = []
        
        # Проверка лимита в секунду
        if len(self.second_history[key]) >= self.calls_per_second:
            oldest_second = min(self.second_history[key])
            wait_times.append(1 - (current_time - oldest_second))
        
        # Проверка лимита в минуту
        if len(self.minute_history[key]) >= self.calls_per_minute:
            oldest_minute = min(self.minute_history[key])
            wait_times.append(60 - (current_time - oldest_minute))
        
        return max(wait_times) if wait_times else 0
    
    def reset(self, key: Optional[str] = None) -> None:
        """Сбросить историю запросов"""
        if key:
            self.minute_history[key].clear()
            self.second_history[key].clear()
        else:
            self.minute_history.clear()
            self.second_history.clear()
    
    def get_stats(self, key: str = "default") -> Dict:
        """Получить статистику использования"""
        current_time = time.time()
        self._cleanup_history(key, current_time)
        
        return {
            'requests_last_minute': len(self.minute_history[key]),
            'requests_last_second': len(self.second_history[key]),
            'limit_per_minute': self.calls_per_minute,
            'limit_per_second': self.calls_per_second,
            'available_minute': self.calls_per_minute - len(self.minute_history[key]),
            'available_second': self.calls_per_second - len(self.second_history[key])
        }


# Глобальный rate limiter для Binance API
binance_limiter = RateLimiter(calls_per_minute=1200, calls_per_second=20)
