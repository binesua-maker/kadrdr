"""
Health Monitoring для системы
"""
import psutil
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class SystemMonitor:
    """Мониторинг состояния системы"""
    
    def __init__(self):
        self.start_time = time.time()
        self.last_check = None
        self.check_history = []
    
    def get_uptime(self) -> timedelta:
        """Получить время работы системы"""
        return timedelta(seconds=int(time.time() - self.start_time))
    
    def get_memory_usage(self) -> Dict:
        """Получить использование памяти"""
        try:
            process = psutil.Process()
            mem_info = process.memory_info()
            
            return {
                'process_mb': round(mem_info.rss / 1024 / 1024, 2),
                'process_percent': round(process.memory_percent(), 2),
                'system_percent': round(psutil.virtual_memory().percent, 2),
                'system_available_mb': round(psutil.virtual_memory().available / 1024 / 1024, 2)
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о памяти: {e}")
            return {'error': str(e)}
    
    def get_cpu_usage(self) -> Dict:
        """Получить использование CPU"""
        try:
            process = psutil.Process()
            
            return {
                'process_percent': round(process.cpu_percent(interval=0.1), 2),
                'system_percent': round(psutil.cpu_percent(interval=0.1), 2),
                'cpu_count': psutil.cpu_count()
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о CPU: {e}")
            return {'error': str(e)}
    
    def get_disk_usage(self) -> Dict:
        """Получить использование диска"""
        try:
            # Определяем путь в зависимости от ОС
            import platform
            if platform.system() == 'Windows':
                disk_path = 'C:\\'
            else:
                disk_path = '/'
            
            disk = psutil.disk_usage(disk_path)
            
            return {
                'total_gb': round(disk.total / 1024 / 1024 / 1024, 2),
                'used_gb': round(disk.used / 1024 / 1024 / 1024, 2),
                'free_gb': round(disk.free / 1024 / 1024 / 1024, 2),
                'percent': round(disk.percent, 2),
                'path': disk_path
            }
        except Exception as e:
            logger.error(f"Ошибка получения информации о диске: {e}")
            return {'error': str(e)}
    
    def check_database(self, db_manager) -> Dict:
        """Проверить подключение к базе данных"""
        try:
            session = db_manager.get_session()
            # Простой запрос для проверки соединения
            session.execute("SELECT 1")
            session.close()
            return {'status': 'ok', 'connected': True}
        except Exception as e:
            logger.error(f"Ошибка подключения к БД: {e}")
            return {'status': 'error', 'connected': False, 'error': str(e)}
    
    def check_cache(self, cache_manager) -> Dict:
        """Проверить подключение к кэшу"""
        try:
            is_connected = cache_manager.is_connected()
            cache_type = 'redis' if cache_manager.redis_client else 'memory'
            
            return {
                'status': 'ok' if is_connected else 'error',
                'connected': is_connected,
                'type': cache_type
            }
        except Exception as e:
            logger.error(f"Ошибка проверки кэша: {e}")
            return {'status': 'error', 'connected': False, 'error': str(e)}
    
    def check_exchange(self, binance_client) -> Dict:
        """Проверить подключение к бирже"""
        try:
            # Попытка получить информацию о сервере
            if hasattr(binance_client, 'exchange') and binance_client.exchange:
                binance_client.exchange.fetch_time()
                return {'status': 'ok', 'connected': True}
            else:
                return {'status': 'not_initialized', 'connected': False}
        except Exception as e:
            logger.error(f"Ошибка подключения к бирже: {e}")
            return {'status': 'error', 'connected': False, 'error': str(e)}
    
    def get_health_status(
        self,
        db_manager=None,
        cache_manager=None,
        binance_client=None
    ) -> Dict:
        """Получить полный статус здоровья системы"""
        health = {
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': str(self.get_uptime()),
            'uptime_seconds': int(time.time() - self.start_time),
            'memory': self.get_memory_usage(),
            'cpu': self.get_cpu_usage(),
            'disk': self.get_disk_usage(),
            'services': {}
        }
        
        # Проверка сервисов
        if db_manager:
            health['services']['database'] = self.check_database(db_manager)
        
        if cache_manager:
            health['services']['cache'] = self.check_cache(cache_manager)
        
        if binance_client:
            health['services']['exchange'] = self.check_exchange(binance_client)
        
        # Общий статус
        all_services_ok = all(
            service.get('status') == 'ok' or service.get('status') == 'not_initialized'
            for service in health['services'].values()
        )
        
        health['overall_status'] = 'healthy' if all_services_ok else 'degraded'
        
        # Сохранить в историю
        self.last_check = health
        self.check_history.append({
            'timestamp': health['timestamp'],
            'status': health['overall_status']
        })
        
        # Ограничить размер истории
        if len(self.check_history) > 100:
            self.check_history = self.check_history[-100:]
        
        return health
    
    def get_summary(self) -> str:
        """Получить текстовое резюме статуса"""
        if not self.last_check:
            return "Мониторинг еще не запускался"
        
        mem = self.last_check.get('memory', {})
        cpu = self.last_check.get('cpu', {})
        services = self.last_check.get('services', {})
        
        summary = f"""
🏥 <b>Состояние системы</b>

⏱ <b>Uptime:</b> {self.last_check.get('uptime', 'N/A')}

💾 <b>Память:</b>
  • Процесс: {mem.get('process_mb', 'N/A')} MB ({mem.get('process_percent', 'N/A')}%)
  • Система: {mem.get('system_percent', 'N/A')}% использовано

🔧 <b>CPU:</b>
  • Процесс: {cpu.get('process_percent', 'N/A')}%
  • Система: {cpu.get('system_percent', 'N/A')}%

📊 <b>Сервисы:</b>
"""
        
        # Добавляем статусы сервисов
        for service_name, service_info in services.items():
            status_icon = '✅' if service_info.get('status') == 'ok' else '❌'
            service_type = service_info.get('type', '')
            type_info = f" ({service_type})" if service_type else ""
            summary += f"  {status_icon} {service_name.title()}{type_info}\n"
        
        overall = self.last_check.get('overall_status', 'unknown')
        overall_icon = '✅' if overall == 'healthy' else '⚠️'
        summary += f"\n{overall_icon} <b>Общий статус:</b> {overall.upper()}"
        
        return summary


# Глобальный монитор
monitor = SystemMonitor()
