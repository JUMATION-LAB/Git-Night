"""
Chat routes for the AI Forex Trading Bot.
Handles user chat messages and generates responses.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import uuid

from models import ChatRequest, ChatResponse
from services.ai_engine import ai_chat_engine
from services.supabase_service import supabase_service
from services.mt5_service import mt5_service
from services.strategy import strategy_service
from utils.logger import logger

router = APIRouter(prefix="/chat", tags=["Chat"])


async def get_or_create_user(user_id: Optional[str] = None) -> str:
    """Get or create a user record."""
    if not user_id:
        user_id = str(uuid.uuid4())
    
    user = await supabase_service.get_user(user_id)
    if not user:
        # Create user with dummy email for now
        await supabase_service.create_user(f"user_{user_id[:8]}@example.com", user_id)
    
    return user_id


@router.post("", response_model=ChatResponse)
async def send_message(request: ChatRequest, user_id: Optional[str] = None):
    """
    Process a chat message and return bot response.
    
    This endpoint:
    1. Parses user intent
    2. Executes actions if needed (trade, analysis, etc.)
    3. Generates intelligent response
    4. Logs conversation
    """
    try:
        # Get or create user
        user_id = await get_or_create_user(user_id)
        
        # Parse message
        parsed = ai_chat_engine.parse_message(request.message)
        logger.info(f"Parsed intent: {parsed['intent']}, action: {parsed['action']}")
        
        # Prepare context for response generation
        context = {}
        
        # Execute action based on intent
        if parsed['action'] == 'GET_ANALYSIS':
            symbol = parsed.get('symbol') or 'EURUSD'
            # Get market data
            df = mt5_service.get_historical_data(symbol, bars=500)
            if df is not None:
                analysis = strategy_service.analyze_market(df, symbol)
                context['analysis'] = analysis
                context['price'] = analysis.get('price')
        
        elif parsed['action'] == 'SHOW_ACCOUNT':
            account_info = mt5_service.get_account_info()
            if account_info:
                context['account'] = {
                    'balance': account_info.balance,
                    'equity': account_info.equity,
                    'free_margin': account_info.free_margin
                }
        
        elif parsed['action'] == 'SHOW_TRADES':
            trades = await supabase_service.get_user_trades(user_id, limit=10)
            context['trades'] = trades
        
        elif parsed['action'] == 'SHOW_STATUS':
            context['status'] = {
                'is_running': mt5_service.is_connected(),
                'auto_trading': auto_trade_state.get('is_running', False),
                'trades_today': await supabase_service.get_trades_today(user_id)
            }
        
        # Generate response
        response = ai_chat_engine.generate_response(parsed, context)
        
        # Log chat message
        await supabase_service.log_chat_message(
            user_id=user_id,
            message=request.message,
            response=response.response,
            intent=response.intent,
            action=response.action
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_chat_history(user_id: Optional[str] = None, limit: int = 50):
    """Get chat history for user."""
    try:
        if not user_id:
            return {"messages": []}
        
        messages = await supabase_service.get_chat_history(user_id, limit)
        return {"messages": messages}
    except Exception as e:
        logger.error(f"Error fetching chat history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Global auto-trade state (in production, use Redis or database)
auto_trade_state = {
    'is_running': False,
    'started_at': None,
    'symbols': ['EURUSD']
}


@router.get("/auto-trade/status")
async def get_auto_trade_status():
    """Get auto-trading status."""
    return auto_trade_state


@router.post("/auto-trade/start")
async def start_auto_trade(symbols: Optional[list] = None, user_id: Optional[str] = None):
    """Start auto-trading."""
    global auto_trade_state
    
    user_id = await get_or_create_user(user_id)
    
    auto_trade_state = {
        'is_running': True,
        'started_at': None,  # Will be set by background task
        'symbols': symbols or ['EURUSD'],
        'user_id': user_id
    }
    
    logger.info(f"Auto-trading started for symbols: {auto_trade_state['symbols']}")
    
    return {
        "status": "success",
        "message": "Auto-trading started",
        "symbols": auto_trade_state['symbols']
    }


@router.post("/auto-trade/stop")
async def stop_auto_trade():
    """Stop auto-trading."""
    global auto_trade_state
    
    auto_trade_state['is_running'] = False
    
    logger.info("Auto-trading stopped")
    
    return {
        "status": "success",
        "message": "Auto-trading stopped"
    }
