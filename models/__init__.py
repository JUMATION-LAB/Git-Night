"""
Pydantic models for the AI Forex Trading Bot.
Defines data structures for users, trades, signals, and chat messages.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class TradeAction(str, Enum):
    """Trade action types."""
    BUY = "BUY"
    SELL = "SELL"
    CLOSE = "CLOSE"


class TradeStatus(str, Enum):
    """Trade status types."""
    PENDING = "PENDING"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class SignalType(str, Enum):
    """Signal type enumeration."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


# User Models
class User(BaseModel):
    """User model."""
    id: str
    email: str
    created_at: datetime
    is_active: bool = True


class UserCreate(BaseModel):
    """User creation model."""
    email: str
    password: str


class UserLogin(BaseModel):
    """User login model."""
    email: str
    password: str


# Trade Models
class Trade(BaseModel):
    """Trade model representing a completed or pending trade."""
    id: Optional[str] = None
    user_id: str
    symbol: str
    action: TradeAction
    lot_size: float
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    close_price: Optional[float] = None
    profit: Optional[float] = None
    status: TradeStatus = TradeStatus.PENDING
    mt5_order_id: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    notes: Optional[str] = None


class TradeCreate(BaseModel):
    """Trade creation request model."""
    symbol: str
    action: TradeAction
    lot_size: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class TradeUpdate(BaseModel):
    """Trade update model."""
    status: Optional[TradeStatus] = None
    close_price: Optional[float] = None
    profit: Optional[float] = None
    closed_at: Optional[datetime] = None


# Signal Models
class Signal(BaseModel):
    """Trading signal model."""
    id: Optional[str] = None
    user_id: str
    symbol: str
    signal_type: SignalType
    strength: float = Field(ge=0, le=100)  # Signal strength percentage
    price: float
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    rsi: Optional[float] = None
    reason: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    executed: bool = False
    trade_id: Optional[str] = None


class SignalCreate(BaseModel):
    """Signal creation model."""
    symbol: str
    signal_type: SignalType
    strength: float
    price: float
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    rsi: Optional[float] = None
    reason: str


# Chat Models
class ChatMessage(BaseModel):
    """Chat message model."""
    id: Optional[str] = None
    user_id: str
    message: str
    response: Optional[str] = None
    intent: Optional[str] = None
    action: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatRequest(BaseModel):
    """Chat request model."""
    message: str
    user_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Chat response model."""
    intent: str
    action: str
    response: str
    data: Optional[dict] = None


# Market Data Models
class OHLCV(BaseModel):
    """OHLCV candle data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class MarketData(BaseModel):
    """Market data response model."""
    symbol: str
    timeframe: str
    candles: List[OHLCV]
    indicators: Optional[dict] = None


# Account Models
class AccountInfo(BaseModel):
    """MetaTrader account information."""
    login: int
    balance: float
    equity: float
    margin: float
    free_margin: float
    profit: float
    leverage: int
    currency: str
    server: str


class Position(BaseModel):
    """Open position model."""
    ticket: int
    symbol: str
    type: TradeAction
    volume: float
    price_open: float
    price_current: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    profit: float
    time: datetime


# Auto Trading Models
class AutoTradeStatus(BaseModel):
    """Auto trading status model."""
    is_running: bool
    started_at: Optional[datetime] = None
    last_run: Optional[datetime] = None
    trades_today: int = 0
    symbols: List[str] = []


class AutoTradeStart(BaseModel):
    """Auto trade start request."""
    symbols: List[str] = ["EURUSD"]
    max_trades_per_day: Optional[int] = None
