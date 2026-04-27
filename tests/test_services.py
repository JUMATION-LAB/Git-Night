"""
Test module for AI Forex Trading Bot.
Run with: pytest tests/ -v
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock


class TestStrategyService:
    """Tests for the strategy service."""
    
    def test_ema_calculation(self):
        """Test EMA calculation."""
        import pandas as pd
        from utils.indicators import calculate_ema
        
        data = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        ema = calculate_ema(data, 3)
        
        assert len(ema) == len(data)
        assert ema.iloc[-1] > ema.iloc[0]
    
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        import pandas as pd
        from utils.indicators import calculate_rsi
        
        # Create price data with some variation
        prices = pd.Series([100, 102, 101, 103, 105, 104, 106, 108, 107, 109] * 10)
        rsi = calculate_rsi(prices, 14)
        
        assert len(rsi) == len(prices)
        assert all((rsi >= 0) & (rsi <= 100))
    
    def test_signal_generation_bullish(self):
        """Test BUY signal generation."""
        from services.strategy import StrategyService
        from models import SignalType
        
        strategy = StrategyService()
        
        # Simulate bullish conditions: EMA50 > EMA200, RSI < 30
        signal_type, strength, reason = strategy._generate_signal(
            ema_50=1.0900,
            ema_200=1.0850,
            rsi=25,
            trend="BULLISH"
        )
        
        assert signal_type == SignalType.BUY
        assert strength > 0
    
    def test_signal_generation_bearish(self):
        """Test SELL signal generation."""
        from services.strategy import StrategyService
        from models import SignalType
        
        strategy = StrategyService()
        
        # Simulate bearish conditions: EMA50 < EMA200, RSI > 70
        signal_type, strength, reason = strategy._generate_signal(
            ema_50=1.0800,
            ema_200=1.0850,
            rsi=75,
            trend="BEARISH"
        )
        
        assert signal_type == SignalType.SELL
        assert strength > 0
    
    def test_signal_generation_hold(self):
        """Test HOLD signal when no clear setup."""
        from services.strategy import StrategyService
        from models import SignalType
        
        strategy = StrategyService()
        
        # Neutral conditions
        signal_type, strength, reason = strategy._generate_signal(
            ema_50=1.0850,
            ema_200=1.0850,
            rsi=50,
            trend="BULLISH"
        )
        
        assert signal_type == SignalType.HOLD


class TestRiskManager:
    """Tests for the risk manager."""
    
    @pytest.mark.asyncio
    async def test_trade_allowed_within_limits(self):
        """Test trade is allowed when within daily limits."""
        from services.risk_manager import RiskManager
        
        risk_manager = RiskManager()
        
        # Mock supabase service to return low trade count
        with patch('services.risk_manager.supabase_service') as mock_supabase:
            mock_supabase.get_trades_today = asyncio.coroutine(lambda x: 1)
            
            allowed, reason = await risk_manager.check_trade_allowed("test_user")
            
            assert allowed is True
    
    def test_position_size_calculation(self):
        """Test position size calculation."""
        from services.risk_manager import RiskManager
        
        risk_manager = RiskManager()
        
        lot_size = risk_manager.calculate_position_size(
            account_balance=10000,
            stop_loss_pips=50,
            symbol="EURUSD"
        )
        
        assert lot_size > 0
        assert lot_size <= 2.0  # Should be reasonable for 10k account
    
    def test_stop_loss_validation_buy(self):
        """Test stop loss validation for BUY trades."""
        from services.risk_manager import RiskManager
        
        risk_manager = RiskManager()
        
        # Valid SL below entry
        valid, msg, sl = risk_manager.validate_stop_loss(
            symbol="EURUSD",
            entry_price=1.0850,
            action="BUY",
            stop_loss=1.0800
        )
        
        assert valid is True
    
    def test_stop_loss_validation_sell(self):
        """Test stop loss validation for SELL trades."""
        from services.risk_manager import RiskManager
        
        risk_manager = RiskManager()
        
        # Valid SL above entry
        valid, msg, sl = risk_manager.validate_stop_loss(
            symbol="EURUSD",
            entry_price=1.0850,
            action="SELL",
            stop_loss=1.0900
        )
        
        assert valid is True


class TestAIChatEngine:
    """Tests for the AI chat engine."""
    
    def test_parse_buy_intent(self):
        """Test parsing BUY intent."""
        from services.ai_engine import AIChatEngine
        
        engine = AIChatEngine()
        parsed = engine.parse_message("Buy EURUSD")
        
        assert parsed['intent'] == 'buy'
        assert parsed['symbol'] == 'EURUSD'
    
    def test_parse_sell_intent(self):
        """Test parsing SELL intent."""
        from services.ai_engine import AIChatEngine
        
        engine = AIChatEngine()
        parsed = engine.parse_message("Sell GBPUSD 0.1 lots")
        
        assert parsed['intent'] == 'sell'
        assert parsed['symbol'] == 'GBPUSD'
        assert parsed['lot_size'] == 0.1
    
    def test_parse_auto_trade_start(self):
        """Test parsing auto-trade start command."""
        from services.ai_engine import AIChatEngine
        
        engine = AIChatEngine()
        parsed = engine.parse_message("Start auto trading")
        
        assert parsed['intent'] == 'auto_trade_start'
        assert parsed['action'] == 'START_AUTO_TRADE'
    
    def test_parse_auto_trade_stop(self):
        """Test parsing auto-trade stop command."""
        from services.ai_engine import AIChatEngine
        
        engine = AIChatEngine()
        parsed = engine.parse_message("Stop auto trading")
        
        assert parsed['intent'] == 'auto_trade_stop'
        assert parsed['action'] == 'STOP_AUTO_TRADE'
    
    def test_parse_trend_query(self):
        """Test parsing trend query."""
        from services.ai_engine import AIChatEngine
        
        engine = AIChatEngine()
        parsed = engine.parse_message("What is the trend?")
        
        assert parsed['intent'] == 'trend'
    
    def test_generate_help_response(self):
        """Test help response generation."""
        from services.ai_engine import AIChatEngine
        
        engine = AIChatEngine()
        parsed = engine.parse_message("help")
        response = engine.generate_response(parsed)
        
        assert 'Available Commands' in response.response or 'help' in response.response.lower()


class TestMT5Service:
    """Tests for MT5 service (mock mode)."""
    
    def test_mock_data_generation(self):
        """Test mock data generation."""
        from services.mt5_service import MT5Service
        
        service = MT5Service()
        df = service._generate_mock_data("EURUSD", bars=100)
        
        assert len(df) == 100
        assert 'open' in df.columns
        assert 'high' in df.columns
        assert 'low' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns
    
    def test_mock_account_info(self):
        """Test mock account info."""
        from services.mt5_service import MT5Service
        
        service = MT5Service()
        account = service.get_account_info()
        
        assert account is not None
        assert account.balance > 0
    
    def test_pip_calculation(self):
        """Test pip calculation."""
        from services.mt5_service import MT5Service
        
        service = MT5Service()
        
        # Standard pairs
        pips = service.calculate_pips("EURUSD", 0.0010)
        assert pips == 10
        
        # JPY pairs
        pips = service.calculate_pips("USDJPY", 1.0)
        assert pips == 100


@pytest.mark.asyncio
async def test_supabase_connection():
    """Test Supabase connection (will skip if not configured)."""
    import os
    from services.supabase_service import SupabaseService
    
    # Skip if not configured
    if not os.getenv('SUPABASE_URL'):
        pytest.skip("Supabase not configured")
    
    service = SupabaseService()
    assert service.client is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
