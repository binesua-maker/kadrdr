# Crypto Screener Bot v2.0 - Testing & Deployment Guide

## 📋 Pre-Deployment Checklist

### 1. Environment Setup

#### Install Dependencies
```bash
cd /path/to/kadrdr/screeeen
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your values:
# - TELEGRAM_BOT_TOKEN (required)
# - ADMIN_USER_IDS (optional, comma-separated)
# - BINANCE_API_KEY (optional, for derivatives features)
# - BINANCE_API_SECRET (optional)
# - REDIS_HOST, REDIS_PORT (optional, auto-fallback to memory)
```

### 2. Database Initialization

The database will be created automatically on first run with all new models:
- User
- UserSettings
- Signal
- ScanHistory
- **Subscription** (NEW)
- **PriceAlert** (NEW)
- **Position** (NEW)
- **ScanSchedule** (NEW)
- **SignalPerformance** (NEW)

### 3. Module Import Tests

Run this to verify all modules import correctly:
```python
python -c "
from utils.cache import cache
from utils.rate_limiter import binance_limiter
from utils.monitoring import monitor
from analysis.mtf_analysis import MTFAnalyzer
from analysis.correlation import CorrelationAnalyzer
from analysis.derivatives import DerivativesAnalyzer
from bot.alerts import AlertManager
from bot.portfolio import PortfolioManager
from data.data_processor import DataProcessor
print('✅ All modules imported successfully')
"
```

## 🧪 Testing Strategy

### Phase 1: Infrastructure Testing

#### Test 1: Cache System
```python
from utils.cache import cache

# Test set/get
cache.set('test_key', {'data': 'value'}, ttl=60)
result = cache.get('test_key')
assert result == {'data': 'value'}

# Test fallback (works without Redis)
print(f"Cache type: {'Redis' if cache.redis_client else 'Memory'}")
```

#### Test 2: Rate Limiter
```python
import asyncio
from utils.rate_limiter import binance_limiter

async def test_rate_limit():
    # Should allow rapid calls up to limit
    for i in range(5):
        await binance_limiter.acquire('test')
        print(f"Request {i+1} allowed")
    
    stats = binance_limiter.get_stats('test')
    print(f"Stats: {stats}")

asyncio.run(test_rate_limit())
```

#### Test 3: System Monitor
```python
from utils.monitoring import monitor
from database.db_manager import DatabaseManager
from data.binance_client import BinanceDataClient
from utils.cache import cache

db = DatabaseManager()
binance = BinanceDataClient()

health = monitor.get_health_status(
    db_manager=db,
    cache_manager=cache,
    binance_client=binance
)

print(monitor.get_summary())
```

### Phase 2: Database Testing

#### Test 4: Database Models & CRUD
```python
from database.db_manager import DatabaseManager
import asyncio

async def test_db():
    db = DatabaseManager()
    
    # Test user creation
    user = await db.create_user(123456789, "testuser")
    print(f"✅ User created: {user.telegram_id}")
    
    # Test subscription
    result = await db.add_subscription(123456789, "BTC/USDT")
    print(f"✅ Subscription added: {result}")
    
    subs = await db.get_user_subscriptions(123456789)
    print(f"✅ Subscriptions: {subs}")
    
    # Test schedule
    schedule_id = await db.create_schedule(123456789, 60, '15m')
    print(f"✅ Schedule created: {schedule_id}")

asyncio.run(test_db())
```

### Phase 3: Analysis Modules Testing

#### Test 5: Multi-Timeframe Analysis
```python
import asyncio
from analysis.mtf_analysis import MTFAnalyzer

async def test_mtf():
    analyzer = MTFAnalyzer()
    result = await analyzer.analyze_symbol('BTC/USDT')
    
    print(analyzer.format_analysis(result))
    print(f"✅ Alignment Score: {result['alignment_score']}")
    print(f"✅ Recommendation: {result['recommendation']}")

asyncio.run(test_mtf())
```

#### Test 6: Correlation Analysis
```python
import asyncio
from analysis.correlation import CorrelationAnalyzer

async def test_correlation():
    analyzer = CorrelationAnalyzer()
    result = await analyzer.analyze_correlation_with_btc('ETH/USDT')
    
    print(analyzer.format_correlation_analysis(result))
    print(f"✅ Correlation: {result.get('correlation', 'N/A')}")

asyncio.run(test_correlation())
```

#### Test 7: Derivatives Analysis
```python
import asyncio
from analysis.derivatives import DerivativesAnalyzer

async def test_derivatives():
    analyzer = DerivativesAnalyzer()
    
    # Test funding rate
    fr_result = await analyzer.get_funding_rate('BTC/USDT')
    print(analyzer.format_funding_rate(fr_result))
    
    # Test OI
    oi_result = await analyzer.get_open_interest('BTC/USDT')
    print(analyzer.format_open_interest(oi_result))

asyncio.run(test_derivatives())
```

### Phase 4: Bot Features Testing

#### Test 8: Alert System
```python
import asyncio
from bot.alerts import AlertManager
from database.db_manager import DatabaseManager

async def test_alerts():
    db = DatabaseManager()
    alert_mgr = AlertManager(db)
    
    # Create user first
    await db.create_user(123456789, "testuser")
    
    # Create alert
    alert = await alert_mgr.create_alert(
        user_id=123456789,
        symbol='BTC/USDT',
        target_price=100000,
        condition='above'
    )
    print(f"✅ Alert created: {alert}")
    
    # Get alerts
    alerts = alert_mgr.get_user_alerts(123456789)
    print(f"✅ User alerts: {alerts}")

asyncio.run(test_alerts())
```

#### Test 9: Portfolio Management
```python
import asyncio
from bot.portfolio import PortfolioManager
from database.db_manager import DatabaseManager

async def test_portfolio():
    db = DatabaseManager()
    portfolio_mgr = PortfolioManager(db)
    
    # Create user first
    await db.create_user(123456789, "testuser")
    
    # Add position
    position = await portfolio_mgr.add_position(
        user_id=123456789,
        symbol='BTC/USDT',
        entry_price=95000,
        quantity=0.5,
        side='long'
    )
    print(f"✅ Position added: {position}")
    
    # Get portfolio
    portfolio = await portfolio_mgr.get_portfolio(123456789)
    print(f"✅ Portfolio: {len(portfolio)} positions")
    
    # Get P&L
    pnl = await portfolio_mgr.get_total_pnl(123456789)
    print(f"✅ Total P&L: ${pnl['total_pnl']}")

asyncio.run(test_portfolio())
```

### Phase 5: Data Processing Testing

#### Test 10: Enhanced Data Processor
```python
import asyncio
from data.data_processor import DataProcessor

async def test_data_processor():
    processor = DataProcessor()
    
    # Test OHLCV with caching
    df = await processor.get_ohlcv('BTC/USDT', '15m', limit=100)
    print(f"✅ OHLCV data: {len(df)} candles")
    
    # Test indicators
    df = processor.add_technical_indicators(df)
    
    # Check new indicators
    assert 'stoch_rsi_k' in df.columns, "Stochastic RSI missing"
    assert 'obv' in df.columns, "OBV missing"
    assert 'vwap' in df.columns, "VWAP missing"
    assert 'adx' in df.columns, "ADX missing"
    
    print("✅ All enhanced indicators present")
    
    # Test pivot points
    pivots = processor.calculate_pivot_points(df)
    print(f"✅ Pivot Points: {pivots}")
    
    # Test trend detection
    trend = processor.determine_trend(df)
    print(f"✅ Trend: {trend['trend']}, Strength: {trend['strength']}")

asyncio.run(test_data_processor())
```

## 🚀 Bot Startup Testing

### Manual Startup Test
```bash
python main.py
```

Expected output:
```
INFO     База данных инициализирована
INFO     DataProcessor: Exchange инициализирована
INFO     Бот инициализирован и готов к работе
INFO     Bot username: @your_bot_username
INFO     Бот успешно запущен! Нажмите Ctrl+C для остановки.
```

### Telegram Bot Commands Test

Once bot is running, test these commands in Telegram:

1. **Basic Commands:**
   - `/start` - Should show welcome message
   - `/help` - Should show command list
   - `/settings` - Should open settings menu

2. **v2.0 Commands:**
   - `/subscribe BTC ETH` - Add subscriptions
   - `/mysubs` - List subscriptions
   - `/alert BTC 100000 above` - Create price alert
   - `/myalerts` - List alerts
   - `/add BTC 95000 0.5 long` - Add position
   - `/portfolio` - View portfolio
   - `/mtf BTC` - Multi-timeframe analysis
   - `/correlation ETH` - Correlation analysis
   - `/funding` - Top funding rates
   - `/health` - System health (admin only)

## 🔍 Common Issues & Solutions

### Issue: "No module named 'redis'"
**Solution:** 
```bash
pip install -r requirements.txt
```

### Issue: "Redis connection failed"
**Expected:** Bot should automatically fallback to in-memory cache
**Verify:** Check logs for "используется in-memory кэш"

### Issue: "Database error"
**Solution:** Delete `screener.db` and restart (will recreate with new schema)

### Issue: "Rate limit exceeded"
**Expected:** Rate limiter should auto-throttle
**Verify:** Check logs for "Rate limit достигнут, ожидание"

### Issue: "Binance API error"
**Solution:** 
- Check internet connection
- Verify API keys (if using derivatives features)
- Check Binance status

## 📊 Performance Benchmarks

Expected performance metrics:

- **Cache hit rate:** >80% for repeated queries
- **Rate limiter overhead:** <10ms per request
- **MTF analysis:** <5 seconds for 4 timeframes
- **Correlation analysis:** <3 seconds per pair
- **Alert check cycle:** <2 seconds for 100 alerts
- **Portfolio P&L calc:** <1 second for 50 positions

## 🏁 Production Deployment

### Pre-Flight Checklist
- [ ] All dependencies installed
- [ ] Environment variables configured
- [ ] Database initialized successfully
- [ ] All module import tests passing
- [ ] Basic bot commands working
- [ ] v2.0 features tested
- [ ] Error handling verified
- [ ] Logging configured properly
- [ ] Rate limiting working
- [ ] Cache system functional

### Monitoring in Production
- Monitor logs/screener.log
- Check /health command regularly
- Monitor memory usage (should be <500MB)
- Watch for rate limit warnings
- Track alert trigger accuracy
- Monitor portfolio calculation accuracy

## 📝 Known Limitations

1. **Derivatives features** require Binance API keys (optional)
2. **Redis** is optional but recommended for production
3. **Alert checking** runs every 10 seconds (configurable)
4. **MTF analysis** limited to 4 timeframes for performance
5. **Rate limiting** uses conservative limits (can be adjusted)

## 🎯 Success Criteria

The v2.0 implementation is considered successful when:

✅ All 10 new features work correctly
✅ Database creates all 5 new models
✅ Cache system handles failures gracefully
✅ Rate limiter prevents API overuse
✅ All analysis modules return valid results
✅ Alert system triggers notifications
✅ Portfolio calculates P&L accurately
✅ Bot handles errors without crashing
✅ Documentation is complete and accurate
✅ Code review findings are addressed

---

**Last Updated:** 2025-01-11
**Version:** 2.0.0
**Status:** Ready for Production Testing
