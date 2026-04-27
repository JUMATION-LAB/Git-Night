"""
Supabase database service for the AI Forex Trading Bot.
Handles all database operations including users, trades, signals, and chat logs.
"""
from supabase import create_client, Client
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import asyncio
from functools import wraps

from config.settings import settings
from utils.logger import logger
from models import (
    Trade, TradeCreate, TradeStatus, TradeAction,
    Signal, SignalCreate, SignalType,
    ChatMessage, ChatRequest,
    User
)


class SupabaseService:
    """Service for interacting with Supabase database."""
    
    def __init__(self):
        """Initialize Supabase client."""
        try:
            self.client: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            self.client = None
    
    def _check_connection(self) -> bool:
        """Check if Supabase connection is available."""
        if self.client is None:
            logger.warning("Supabase client not initialized")
            return False
        return True
    
    # User Operations
    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        if not self._check_connection():
            return None
        
        try:
            response = self.client.table("users").select("*").eq("id", user_id).execute()
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching user: {e}")
            return None
    
    async def create_user(self, email: str, user_id: str) -> Optional[User]:
        """Create a new user record."""
        if not self._check_connection():
            return None
        
        try:
            data = {
                "id": user_id,
                "email": email,
                "created_at": datetime.utcnow().isoformat(),
                "is_active": True
            }
            response = self.client.table("users").insert(data).execute()
            if response.data and len(response.data) > 0:
                return User(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None
    
    # Trade Operations
    async def create_trade(self, trade: TradeCreate, user_id: str) -> Optional[Trade]:
        """Create a new trade record."""
        if not self._check_connection():
            return None
        
        try:
            data = {
                "user_id": user_id,
                "symbol": trade.symbol,
                "action": trade.action.value,
                "lot_size": trade.lot_size or settings.DEFAULT_LOT_SIZE,
                "stop_loss": trade.stop_loss,
                "take_profit": trade.take_profit,
                "status": TradeStatus.PENDING.value,
                "created_at": datetime.utcnow().isoformat()
            }
            response = self.client.table("trades").insert(data).execute()
            if response.data and len(response.data) > 0:
                return Trade(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating trade: {e}")
            return None
    
    async def update_trade(self, trade_id: str, updates: Dict[str, Any]) -> Optional[Trade]:
        """Update an existing trade."""
        if not self._check_connection():
            return None
        
        try:
            response = self.client.table("trades").update(updates).eq("id", trade_id).execute()
            if response.data and len(response.data) > 0:
                return Trade(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating trade: {e}")
            return None
    
    async def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get trade by ID."""
        if not self._check_connection():
            return None
        
        try:
            response = self.client.table("trades").select("*").eq("id", trade_id).execute()
            if response.data and len(response.data) > 0:
                return Trade(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error fetching trade: {e}")
            return None
    
    async def get_user_trades(self, user_id: str, limit: int = 50) -> List[Trade]:
        """Get all trades for a user."""
        if not self._check_connection():
            return []
        
        try:
            response = self.client.table("trades")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return [Trade(**trade) for trade in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error fetching user trades: {e}")
            return []
    
    async def get_trades_today(self, user_id: str) -> int:
        """Get count of trades executed today."""
        if not self._check_connection():
            return 0
        
        try:
            today = date.today().isoformat()
            response = self.client.table("trades")\
                .select("id", count="exact")\
                .eq("user_id", user_id)\
                .gte("created_at", today)\
                .in_("status", [TradeStatus.OPEN.value, TradeStatus.CLOSED.value])\
                .execute()
            return response.count if hasattr(response, 'count') else 0
        except Exception as e:
            logger.error(f"Error counting today's trades: {e}")
            return 0
    
    # Signal Operations
    async def create_signal(self, signal: SignalCreate, user_id: str) -> Optional[Signal]:
        """Create a new trading signal."""
        if not self._check_connection():
            return None
        
        try:
            data = {
                "user_id": user_id,
                "symbol": signal.symbol,
                "signal_type": signal.signal_type.value,
                "strength": signal.strength,
                "price": signal.price,
                "ema_50": signal.ema_50,
                "ema_200": signal.ema_200,
                "rsi": signal.rsi,
                "reason": signal.reason,
                "executed": False,
                "created_at": datetime.utcnow().isoformat()
            }
            response = self.client.table("signals").insert(data).execute()
            if response.data and len(response.data) > 0:
                return Signal(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error creating signal: {e}")
            return None
    
    async def update_signal(self, signal_id: str, executed: bool = False, trade_id: Optional[str] = None) -> Optional[Signal]:
        """Update a signal after execution."""
        if not self._check_connection():
            return None
        
        try:
            updates = {"executed": executed}
            if trade_id:
                updates["trade_id"] = trade_id
            
            response = self.client.table("signals").update(updates).eq("id", signal_id).execute()
            if response.data and len(response.data) > 0:
                return Signal(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error updating signal: {e}")
            return None
    
    async def get_recent_signals(self, user_id: str, limit: int = 20) -> List[Signal]:
        """Get recent signals for a user."""
        if not self._check_connection():
            return []
        
        try:
            response = self.client.table("signals")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return [Signal(**sig) for sig in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error fetching signals: {e}")
            return []
    
    # Chat Log Operations
    async def log_chat_message(self, user_id: str, message: str, response: str, 
                               intent: Optional[str] = None, action: Optional[str] = None) -> Optional[ChatMessage]:
        """Log a chat message and response."""
        if not self._check_connection():
            return None
        
        try:
            data = {
                "user_id": user_id,
                "message": message,
                "response": response,
                "intent": intent,
                "action": action,
                "created_at": datetime.utcnow().isoformat()
            }
            response = self.client.table("chat_logs").insert(data).execute()
            if response.data and len(response.data) > 0:
                return ChatMessage(**response.data[0])
            return None
        except Exception as e:
            logger.error(f"Error logging chat message: {e}")
            return None
    
    async def get_chat_history(self, user_id: str, limit: int = 50) -> List[ChatMessage]:
        """Get chat history for a user."""
        if not self._check_connection():
            return []
        
        try:
            response = self.client.table("chat_logs")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()
            return [ChatMessage(**msg) for msg in response.data] if response.data else []
        except Exception as e:
            logger.error(f"Error fetching chat history: {e}")
            return []
    
    # Settings Operations
    async def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Get user settings."""
        if not self._check_connection():
            return {}
        
        try:
            response = self.client.table("settings").select("*").eq("user_id", user_id).execute()
            if response.data and len(response.data) > 0:
                return response.data[0].get("settings", {})
            return {}
        except Exception as e:
            logger.error(f"Error fetching user settings: {e}")
            return {}
    
    async def update_user_settings(self, user_id: str, settings_dict: Dict[str, Any]) -> bool:
        """Update user settings."""
        if not self._check_connection():
            return False
        
        try:
            # Check if settings exist
            response = self.client.table("settings").select("id").eq("user_id", user_id).execute()
            
            if response.data and len(response.data) > 0:
                # Update existing
                self.client.table("settings").update({
                    "settings": settings_dict,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("user_id", user_id).execute()
            else:
                # Insert new
                self.client.table("settings").insert({
                    "user_id": user_id,
                    "settings": settings_dict,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            return False
    
    # Analytics Operations
    async def get_trade_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get trading statistics for a user."""
        if not self._check_connection():
            return {}
        
        try:
            # Get all closed trades
            response = self.client.table("trades")\
                .select("profit, status, action")\
                .eq("user_id", user_id)\
                .eq("status", TradeStatus.CLOSED.value)\
                .execute()
            
            trades = response.data if response.data else []
            
            if not trades:
                return {
                    "total_trades": 0,
                    "winning_trades": 0,
                    "losing_trades": 0,
                    "win_rate": 0.0,
                    "total_profit": 0.0,
                    "average_profit": 0.0
                }
            
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.get('profit', 0) > 0)
            losing_trades = total_trades - winning_trades
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            total_profit = sum(t.get('profit', 0) for t in trades)
            average_profit = total_profit / total_trades if total_trades > 0 else 0
            
            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": round(win_rate, 2),
                "total_profit": round(total_profit, 2),
                "average_profit": round(average_profit, 2)
            }
        except Exception as e:
            logger.error(f"Error calculating trade statistics: {e}")
            return {}


# Global service instance
supabase_service = SupabaseService()
