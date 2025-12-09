"""
Redis кэширование с fallback на in-memory cache
"""
import json
import time
from typing import Any, Optional
from loguru import logger
import os

# Попытка импорта redis
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis не установлен, используется in-memory кэш")


class CacheManager:
    """Менеджер кэширования с поддержкой Redis и fallback на память"""
    
    def __init__(self):
        self.redis_client = None
        self.memory_cache = {}
        self.cache_ttl = {}
        
        # Попытка подключения к Redis
        if REDIS_AVAILABLE:
            try:
                redis_host = os.getenv('REDIS_HOST', 'localhost')
                redis_port = int(os.getenv('REDIS_PORT', 6379))
                redis_db = int(os.getenv('REDIS_DB', 0))
                redis_password = os.getenv('REDIS_PASSWORD', None)
                
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=True,
                    socket_timeout=5,
                    socket_connect_timeout=5
                )
                
                # Проверка подключения
                self.redis_client.ping()
                logger.info(f"Подключено к Redis на {redis_host}:{redis_port}")
                
            except Exception as e:
                logger.warning(f"Не удалось подключиться к Redis: {e}. Используется in-memory кэш")
                self.redis_client = None
    
    def get(self, key: str) -> Optional[Any]:
        """Получить значение из кэша"""
        try:
            if self.redis_client:
                # Redis кэш
                value = self.redis_client.get(key)
                if value:
                    return json.loads(value)
                return None
            else:
                # Memory кэш
                if key in self.memory_cache:
                    # Проверка TTL
                    if key in self.cache_ttl:
                        if time.time() > self.cache_ttl[key]:
                            del self.memory_cache[key]
                            del self.cache_ttl[key]
                            return None
                    return self.memory_cache[key]
                return None
                
        except Exception as e:
            logger.error(f"Ошибка чтения из кэша: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """Сохранить значение в кэш с TTL в секундах"""
        try:
            if self.redis_client:
                # Redis кэш
                self.redis_client.setex(
                    key,
                    ttl,
                    json.dumps(value, default=str)
                )
                return True
            else:
                # Memory кэш
                self.memory_cache[key] = value
                self.cache_ttl[key] = time.time() + ttl
                return True
                
        except Exception as e:
            logger.error(f"Ошибка записи в кэш: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Удалить ключ из кэша"""
        try:
            if self.redis_client:
                self.redis_client.delete(key)
                return True
            else:
                if key in self.memory_cache:
                    del self.memory_cache[key]
                if key in self.cache_ttl:
                    del self.cache_ttl[key]
                return True
                
        except Exception as e:
            logger.error(f"Ошибка удаления из кэша: {e}")
            return False
    
    def clear(self) -> bool:
        """Очистить весь кэш"""
        try:
            if self.redis_client:
                self.redis_client.flushdb()
                return True
            else:
                self.memory_cache.clear()
                self.cache_ttl.clear()
                return True
                
        except Exception as e:
            logger.error(f"Ошибка очистки кэша: {e}")
            return False
    
    def is_connected(self) -> bool:
        """Проверить подключение к кэшу"""
        try:
            if self.redis_client:
                self.redis_client.ping()
                return True
            return True  # Memory cache всегда доступен
        except Exception:
            return False


# Глобальный экземпляр кэша
cache = CacheManager()
