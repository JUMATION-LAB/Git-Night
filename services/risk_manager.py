"""
Risk management service for the AI Forex Trading Bot.
Implements strict risk controls to protect capital.
"""
from typing import Optional, Tuple
from datetime import date

from config.settings import settings
from utils.logger import logger
from services.supabase_service import supabase_service


class RiskManager:
    """
    Risk management service implementing trading rules and limits.
    
    Rules:
    - Max 2% risk per trade
    - Max 3 trades per day
    - Mandatory stop loss
    - Reject trade if risk rules fail
    """
    
    def __init__(self):
        """Initialize risk manager."""
        self.max_risk_percent = settings.MAX_RISK_PERCENT
        self.max_trades_per_day = settings.MAX_TRADES_PER_DAY
        self.default_stop_loss_pips = settings.DEFAULT_STOP_LOSS_PIPS
        self.default_take_profit_pips = settings.DEFAULT_TAKE_PROFIT_PIPS
    
    async def check_trade_allowed(self, user_id: str) -> Tuple[bool, str]:
        """
        Check if a new trade is allowed based on risk rules.
        
        Args:
            user_id: User identifier
            
        Returns:
            Tuple of (allowed: bool, reason: str)
        """
        # Check daily trade limit
        trades_today = await supabase_service.get_trades_today(user_id)
        
        if trades_today >= self.max_trades_per_day:
            return False, f"Daily trade limit reached ({trades_today}/{self.max_trades_per_day})"
        
        logger.info(f"Risk check passed: {trades_today} trades today")
        return True, "Trade allowed"
    
    def calculate_position_size(self, account_balance: float, stop_loss_pips: float, 
                               symbol: str = "EURUSD") -> float:
        """
        Calculate safe position size based on risk percentage.
        
        Args:
            account_balance: Account balance in account currency
            stop_loss_pips: Stop loss in pips
            symbol: Trading symbol
            
        Returns:
            Lot size
        """
        # Risk amount in account currency
        risk_amount = account_balance * (self.max_risk_percent / 100)
        
        # Pip value per standard lot (approximate)
        # For EURUSD: 1 pip = $10 per standard lot
        # This is simplified - real calculation would use current exchange rates
        pip_value_per_lot = 10.0
        
        if "JPY" in symbol:
            pip_value_per_lot = 7.5  # Approximate for JPY pairs
        
        # Calculate lot size
        if stop_loss_pips <= 0:
            stop_loss_pips = self.default_stop_loss_pips
        
        lot_size = risk_amount / (stop_loss_pips * pip_value_per_lot)
        
        # Round to nearest 0.01 lot
        lot_size = round(lot_size, 2)
        
        # Ensure minimum lot size
        min_lot = 0.01
        if lot_size < min_lot:
            lot_size = min_lot
        
        logger.info(f"Calculated position size: {lot_size} lots (risk: {self.max_risk_percent}%, SL: {stop_loss_pips} pips)")
        return lot_size
    
    def validate_stop_loss(self, symbol: str, entry_price: float, 
                          action: str, stop_loss: Optional[float]) -> Tuple[bool, str, float]:
        """
        Validate and adjust stop loss if necessary.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            action: BUY or SELL
            stop_loss: Proposed stop loss price
            
        Returns:
            Tuple of (valid: bool, message: str, adjusted_sl: float)
        """
        if stop_loss is None:
            # Auto-calculate stop loss
            sl_pips = self.default_stop_loss_pips
            sl_price = self._calculate_sl_price(symbol, entry_price, action, sl_pips)
            return True, f"Auto-calculated SL: {sl_price}", sl_price
        
        # Validate SL is on correct side
        if action == "BUY":
            if stop_loss >= entry_price:
                return False, "Stop loss must be below entry price for BUY", stop_loss
        else:  # SELL
            if stop_loss <= entry_price:
                return False, "Stop loss must be above entry price for SELL", stop_loss
        
        # Check SL distance
        sl_distance_pips = self._pips_difference(symbol, entry_price, stop_loss)
        
        if sl_distance_pips < 5:
            return False, f"Stop loss too close ({sl_distance_pips:.1f} pips, min 5)", stop_loss
        
        if sl_distance_pips > 200:
            return False, f"Stop loss too far ({sl_distance_pips:.1f} pips, max 200)", stop_loss
        
        return True, f"Stop loss validated: {sl_distance_pips:.1f} pips", stop_loss
    
    def validate_take_profit(self, symbol: str, entry_price: float,
                            action: str, take_profit: Optional[float],
                            stop_loss: float) -> Tuple[bool, str, Optional[float]]:
        """
        Validate take profit level.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            action: BUY or SELL
            take_profit: Proposed take profit price
            stop_loss: Stop loss price
            
        Returns:
            Tuple of (valid: bool, message: str, adjusted_tp: float or None)
        """
        if take_profit is None:
            # Auto-calculate take profit (2:1 reward:risk ratio)
            tp_pips = self.default_take_profit_pips
            tp_price = self._calculate_tp_price(symbol, entry_price, action, tp_pips)
            return True, f"Auto-calculated TP: {tp_price}", tp_price
        
        # Validate TP is on correct side
        if action == "BUY":
            if take_profit <= entry_price:
                return False, "Take profit must be above entry price for BUY", take_profit
        else:  # SELL
            if take_profit >= entry_price:
                return False, "Take profit must be below entry price for SELL", take_profit
        
        # Check risk:reward ratio
        sl_distance = abs(entry_price - stop_loss)
        tp_distance = abs(take_profit - entry_price)
        
        if sl_distance == 0:
            return False, "Invalid stop loss for R:R calculation", take_profit
        
        rr_ratio = tp_distance / sl_distance
        
        if rr_ratio < 1.0:
            return False, f"Risk:Reward ratio too low ({rr_ratio:.2f}:1, min 1:1)", take_profit
        
        return True, f"Take profit validated: R:R = {rr_ratio:.2f}:1", take_profit
    
    def _calculate_sl_price(self, symbol: str, entry_price: float, 
                           action: str, pips: float) -> float:
        """Calculate stop loss price from pips."""
        pip_value = self._get_pip_value(symbol)
        
        if action == "BUY":
            return round(entry_price - (pips * pip_value), 5)
        else:
            return round(entry_price + (pips * pip_value), 5)
    
    def _calculate_tp_price(self, symbol: str, entry_price: float,
                           action: str, pips: float) -> float:
        """Calculate take profit price from pips."""
        pip_value = self._get_pip_value(symbol)
        
        if action == "BUY":
            return round(entry_price + (pips * pip_value), 5)
        else:
            return round(entry_price - (pips * pip_value), 5)
    
    def _get_pip_value(self, symbol: str) -> float:
        """Get pip value multiplier for symbol."""
        if "JPY" in symbol:
            return 0.01
        else:
            return 0.0001
    
    def _pips_difference(self, symbol: str, price1: float, price2: float) -> float:
        """Calculate difference in pips between two prices."""
        diff = abs(price1 - price2)
        pip_value = self._get_pip_value(symbol)
        return diff / pip_value
    
    def get_risk_summary(self, user_id: str) -> dict:
        """
        Get risk summary for user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with risk metrics
        """
        trades_today = 0  # Would need to fetch from database
        
        return {
            "max_risk_percent": self.max_risk_percent,
            "max_trades_per_day": self.max_trades_per_day,
            "trades_today": trades_today,
            "remaining_trades": max(0, self.max_trades_per_day - trades_today),
            "default_stop_loss_pips": self.default_stop_loss_pips,
            "default_take_profit_pips": self.default_take_profit_pips
        }


# Global risk manager instance
risk_manager = RiskManager()
