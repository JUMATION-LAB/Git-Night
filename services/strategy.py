"""
Trading strategy service for the AI Forex Trading Bot.
Implements EMA crossover + RSI strategy with signal generation.
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import pandas as pd

from utils.logger import logger
from utils.indicators import get_indicator_values
from models import SignalType, SignalCreate
from services.supabase_service import supabase_service


class StrategyService:
    """
    Trading strategy service implementing technical analysis.
    
    Strategy Rules:
    - BUY: EMA50 > EMA200 AND RSI < 30 (oversold in uptrend)
    - SELL: EMA50 < EMA200 AND RSI > 70 (overbought in downtrend)
    """
    
    def __init__(self):
        """Initialize strategy service."""
        self.ema_fast_period = 50
        self.ema_slow_period = 200
        self.rsi_period = 14
        self.rsi_oversold = 30
        self.rsi_overbought = 70
    
    def analyze_market(self, df: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        Analyze market data and generate trading signals.
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Trading symbol
            
        Returns:
            Dictionary with analysis results
        """
        try:
            # Calculate indicators
            indicators = get_indicator_values(df)
            
            latest = indicators['latest']
            previous = indicators['previous']
            
            ema_50 = latest['ema_50']
            ema_200 = latest['ema_200']
            rsi = latest['rsi']
            current_price = latest['current_price']
            
            # Determine trend
            if ema_50 > ema_200:
                trend = "BULLISH"
            else:
                trend = "BEARISH"
            
            # Generate signal
            signal_type, strength, reason = self._generate_signal(
                ema_50, ema_200, rsi, trend
            )
            
            return {
                "symbol": symbol,
                "timestamp": datetime.utcnow(),
                "price": current_price,
                "trend": trend,
                "indicators": {
                    "ema_50": ema_50,
                    "ema_200": ema_200,
                    "rsi": rsi,
                    "ema_spread": ((ema_50 - ema_200) / ema_200 * 100),
                    "ema_spread_pips": (ema_50 - ema_200) * 10000
                },
                "signal": {
                    "type": signal_type.value,
                    "strength": strength,
                    "reason": reason
                }
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market for {symbol}: {e}")
            return {
                "symbol": symbol,
                "error": str(e),
                "signal": {"type": "HOLD", "strength": 0, "reason": "Analysis failed"}
            }
    
    def _generate_signal(self, ema_50: float, ema_200: float, 
                        rsi: float, trend: str) -> tuple:
        """
        Generate trading signal based on indicator values.
        
        Args:
            ema_50: 50-period EMA value
            ema_200: 200-period EMA value
            rsi: RSI value
            trend: Current trend (BULLISH/BEARISH)
            
        Returns:
            Tuple of (SignalType, strength, reason)
        """
        # Calculate EMA spread percentage
        ema_spread_pct = abs((ema_50 - ema_200) / ema_200 * 100)
        
        # BUY signal: Uptrend + Oversold
        if trend == "BULLISH" and rsi < self.rsi_oversold:
            strength = self._calculate_strength(ema_spread_pct, rsi, self.rsi_oversold)
            reason = f"Bullish trend (EMA50>EMA200 by {ema_spread_pct:.2f}%) + RSI oversold ({rsi:.1f})"
            return SignalType.BUY, strength, reason
        
        # SELL signal: Downtrend + Overbought
        if trend == "BEARISH" and rsi > self.rsi_overbought:
            strength = self._calculate_strength(ema_spread_pct, rsi, self.rsi_overbought, is_sell=True)
            reason = f"Bearish trend (EMA50<EMA200 by {ema_spread_pct:.2f}%) + RSI overbought ({rsi:.1f})"
            return SignalType.SELL, strength, reason
        
        # HOLD: No clear signal
        return SignalType.HOLD, 0, f"No signal - Trend: {trend}, RSI: {rsi:.1f}"
    
    def _calculate_strength(self, ema_spread_pct: float, rsi: float, 
                           threshold: float, is_sell: bool = False) -> float:
        """
        Calculate signal strength (0-100).
        
        Args:
            ema_spread_pct: EMA spread percentage
            rsi: RSI value
            threshold: RSI threshold
            is_sell: Whether this is a sell signal
            
        Returns:
            Strength percentage
        """
        # Base strength from EMA spread (max 40 points)
        spread_strength = min(ema_spread_pct * 10, 40)
        
        # RSI strength (max 60 points)
        if is_sell:
            rsi_strength = min((rsi - threshold) * 2, 60)
        else:
            rsi_strength = min((threshold - rsi) * 2, 60)
        
        total_strength = spread_strength + rsi_strength
        return min(max(total_strength, 0), 100)  # Clamp to 0-100
    
    async def create_signal_record(self, user_id: str, symbol: str, 
                                   analysis: Dict[str, Any]) -> Optional[str]:
        """
        Create a signal record in the database.
        
        Args:
            user_id: User identifier
            symbol: Trading symbol
            analysis: Analysis results
            
        Returns:
            Signal ID if created, None otherwise
        """
        try:
            signal_data = analysis.get('signal', {})
            indicators = analysis.get('indicators', {})
            
            signal_create = SignalCreate(
                symbol=symbol,
                signal_type=SignalType(signal_data.get('type', 'HOLD')),
                strength=signal_data.get('strength', 0),
                price=analysis.get('price', 0),
                ema_50=indicators.get('ema_50'),
                ema_200=indicators.get('ema_200'),
                rsi=indicators.get('rsi'),
                reason=signal_data.get('reason', '')
            )
            
            signal = await supabase_service.create_signal(signal_create, user_id)
            
            if signal:
                logger.info(f"Signal created: {signal.id} - {signal.signal_type.value} {symbol}")
                return signal.id
            
            return None
            
        except Exception as e:
            logger.error(f"Error creating signal record: {e}")
            return None
    
    def should_execute_signal(self, signal_strength: float, 
                             min_strength: float = 60.0) -> bool:
        """
        Determine if a signal should be executed based on strength.
        
        Args:
            signal_strength: Signal strength (0-100)
            min_strength: Minimum strength required for execution
            
        Returns:
            True if signal should be executed
        """
        return signal_strength >= min_strength
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get information about the current strategy."""
        return {
            "name": "EMA Crossover + RSI",
            "description": "Combines trend following (EMA crossover) with mean reversion (RSI)",
            "parameters": {
                "ema_fast_period": self.ema_fast_period,
                "ema_slow_period": self.ema_slow_period,
                "rsi_period": self.rsi_period,
                "rsi_oversold": self.rsi_oversold,
                "rsi_overbought": self.rsi_overbought
            },
            "rules": {
                "buy": f"EMA{self.ema_fast_period} > EMA{self.ema_slow_period} AND RSI < {self.rsi_oversold}",
                "sell": f"EMA{self.ema_fast_period} < EMA{self.ema_slow_period} AND RSI > {self.rsi_overbought}"
            }
        }


# Global strategy service instance
strategy_service = StrategyService()
