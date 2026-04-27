"""
Trade routes for the AI Forex Trading Bot.
Handles manual trade execution and position management.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional, List
import uuid

from models import TradeCreate, Trade, TradeAction, TradeStatus
from services.mt5_service import mt5_service
from services.supabase_service import supabase_service
from services.risk_manager import risk_manager
from services.strategy import strategy_service
from utils.logger import logger

router = APIRouter(prefix="/trade", tags=["Trading"])


async def get_or_create_user(user_id: Optional[str] = None) -> str:
    """Get or create a user record."""
    if not user_id:
        user_id = str(uuid.uuid4())
    
    user = await supabase_service.get_user(user_id)
    if not user:
        await supabase_service.create_user(f"user_{user_id[:8]}@example.com", user_id)
    
    return user_id


@router.post("", response_model=Trade)
async def execute_trade(trade_request: TradeCreate, user_id: Optional[str] = None):
    """
    Execute a manual trade.
    
    This endpoint:
    1. Validates risk parameters
    2. Places order via MT5
    3. Records trade in database
    """
    try:
        user_id = await get_or_create_user(user_id)
        
        # Check if trade is allowed
        allowed, reason = await risk_manager.check_trade_allowed(user_id)
        if not allowed:
            raise HTTPException(status_code=400, detail=reason)
        
        # Get account info for position sizing
        account_info = mt5_service.get_account_info()
        if not account_info:
            raise HTTPException(status_code=500, detail="Cannot get account information")
        
        # Calculate position size if not specified
        lot_size = trade_request.lot_size
        if not lot_size:
            lot_size = risk_manager.calculate_position_size(
                account_info.balance,
                settings.DEFAULT_STOP_LOSS_PIPS,
                trade_request.symbol
            )
        
        # Get current price for SL/TP calculation
        df = mt5_service.get_historical_data(trade_request.symbol, bars=10)
        if df is None:
            raise HTTPException(status_code=500, detail=f"Cannot get price data for {trade_request.symbol}")
        
        current_price = df['close'].iloc[-1]
        
        # Validate/Calculate stop loss
        sl_valid, sl_msg, sl_price = risk_manager.validate_stop_loss(
            trade_request.symbol,
            current_price,
            trade_request.action.value,
            trade_request.stop_loss
        )
        
        if not sl_valid:
            raise HTTPException(status_code=400, detail=sl_msg)
        
        # Validate/Calculate take profit
        tp_valid, tp_msg, tp_price = risk_manager.validate_take_profit(
            trade_request.symbol,
            current_price,
            trade_request.action.value,
            trade_request.take_profit,
            sl_price
        )
        
        if not tp_valid:
            raise HTTPException(status_code=400, detail=tp_msg)
        
        # Place order via MT5
        order_ticket = mt5_service.place_order(
            symbol=trade_request.symbol,
            action=trade_request.action,
            lot_size=lot_size,
            stop_loss=sl_price,
            take_profit=tp_price
        )
        
        if not order_ticket:
            raise HTTPException(status_code=500, detail="Failed to place order")
        
        # Create trade record
        trade_data = TradeCreate(
            symbol=trade_request.symbol,
            action=trade_request.action,
            lot_size=lot_size,
            stop_loss=sl_price,
            take_profit=tp_price
        )
        
        trade = await supabase_service.create_trade(trade_data, user_id)
        
        if not trade:
            logger.warning("Order placed but failed to create trade record")
            # Order was placed, return basic info
            return Trade(
                user_id=user_id,
                symbol=trade_request.symbol,
                action=trade_request.action,
                lot_size=lot_size,
                entry_price=current_price,
                stop_loss=sl_price,
                take_profit=tp_price,
                status=TradeStatus.OPEN,
                mt5_order_id=order_ticket
            )
        
        # Update trade with MT5 order ID
        await supabase_service.update_trade(trade.id, {
            "mt5_order_id": order_ticket,
            "entry_price": current_price,
            "status": TradeStatus.OPEN.value
        })
        
        logger.info(f"Trade executed: {trade.id} - {trade_request.action.value} {lot_size} lots {trade_request.symbol}")
        
        return trade
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close/{ticket}")
async def close_trade(ticket: int, user_id: Optional[str] = None):
    """Close an open position by ticket number."""
    try:
        success = mt5_service.close_position(ticket)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to close position")
        
        # Update trade record in database
        # (In production, you'd fetch the trade and update it)
        
        return {
            "status": "success",
            "message": f"Position {ticket} closed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=List[dict])
async def get_positions():
    """Get all open positions."""
    try:
        positions = mt5_service.get_open_positions()
        return [pos.dict() for pos in positions]
    except Exception as e:
        logger.error(f"Error getting positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[Trade])
async def get_trade_history(user_id: Optional[str] = None, limit: int = 50):
    """Get trade history for user."""
    try:
        if not user_id:
            return []
        
        trades = await supabase_service.get_user_trades(user_id, limit)
        return trades
    except Exception as e:
        logger.error(f"Error fetching trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
async def get_statistics(user_id: Optional[str] = None):
    """Get trading statistics for user."""
    try:
        if not user_id:
            return {"error": "User ID required"}
        
        stats = await supabase_service.get_trade_statistics(user_id)
        return stats
    except Exception as e:
        logger.error(f"Error fetching statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis/{symbol}")
async def get_market_analysis(symbol: str):
    """Get market analysis for a symbol."""
    try:
        # Get historical data
        df = mt5_service.get_historical_data(symbol, bars=500)
        
        if df is None:
            raise HTTPException(status_code=404, detail=f"No data available for {symbol}")
        
        # Analyze market
        analysis = strategy_service.analyze_market(df, symbol)
        
        return analysis
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing market: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Import settings here to avoid circular import
from config.settings import settings
