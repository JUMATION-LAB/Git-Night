"""
Main FastAPI application entry point.
Sets up routes, middleware, and background tasks.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from config.settings import settings
from utils.logger import logger
from services.mt5_service import mt5_service
from services.supabase_service import supabase_service
from routes import chat, trade, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(f"Starting {settings.APP_NAME}...")
    
    # Connect to MT5
    await mt5_service.connect()
    
    # Start auto-trading loop
    auto_trade_task = asyncio.create_task(auto_trading_loop())
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    auto_trade_task.cancel()
    await mt5_service.disconnect()


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered forex trading chatbot with automated trading capabilities",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(trade.router)


# Auto-trading background task
async def auto_trading_loop():
    """
    Background task that runs auto-trading logic every minute.
    """
    from services.strategy import strategy_service
    from services.risk_manager import risk_manager
    from routes.chat import auto_trade_state
    
    logger.info("Auto-trading loop started")
    
    while True:
        try:
            # Check if auto-trading is enabled
            if not auto_trade_state.get('is_running', False):
                await asyncio.sleep(5)  # Check every 5 seconds if disabled
                continue
            
            user_id = auto_trade_state.get('user_id')
            symbols = auto_trade_state.get('symbols', ['EURUSD'])
            
            for symbol in symbols:
                try:
                    # Get market data
                    df = mt5_service.get_historical_data(symbol, bars=500)
                    
                    if df is None:
                        logger.warning(f"No data for {symbol}")
                        continue
                    
                    # Analyze market
                    analysis = strategy_service.analyze_market(df, symbol)
                    
                    signal = analysis.get('signal', {})
                    
                    # Check if we should trade
                    if signal.get('type') != 'HOLD':
                        strength = signal.get('strength', 0)
                        
                        # Only trade if signal strength is high enough
                        if strategy_service.should_execute_signal(strength, min_strength=60):
                            # Check risk limits
                            allowed, reason = await risk_manager.check_trade_allowed(user_id)
                            
                            if allowed:
                                # Execute trade
                                logger.info(f"Auto-trade signal: {signal.get('type')} {symbol} - {signal.get('reason')}")
                                
                                # In production, execute the trade here
                                # For now, just log the signal
                                
                                # Create signal record
                                if user_id:
                                    await strategy_service.create_signal_record(
                                        user_id, symbol, analysis
                                    )
                    
                except Exception as e:
                    logger.error(f"Error in auto-trading for {symbol}: {e}")
            
            # Update last run time
            from datetime import datetime
            auto_trade_state['last_run'] = datetime.utcnow()
            
            # Wait 1 minute before next iteration
            await asyncio.sleep(60)
            
        except asyncio.CancelledError:
            logger.info("Auto-trading loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error in auto-trading loop: {e}")
            await asyncio.sleep(10)  # Wait before retrying


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "status": "running",
        "mt5_connected": mt5_service.is_connected(),
        "mock_mode": mt5_service.mock_mode,
        "docs": "/docs"
    }


@app.get("/status")
async def get_status():
    """Get bot status."""
    from routes.chat import auto_trade_state
    
    account_info = mt5_service.get_account_info()
    
    return {
        "bot_running": True,
        "mt5_connected": mt5_service.is_connected(),
        "mock_mode": mt5_service.mock_mode,
        "auto_trading": auto_trade_state.get('is_running', False),
        "account": {
            "balance": account_info.balance if account_info else None,
            "equity": account_info.equity if account_info else None,
            "currency": account_info.currency if account_info else None
        } if account_info else None
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )
