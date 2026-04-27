"""
MetaTrader 5 service for the AI Forex Trading Bot.
Handles MT5 connection, trade execution, and market data retrieval.
Includes mock mode for testing without real MT5 connection.
"""
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime
import pandas as pd

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    mt5 = None

from config.settings import settings
from utils.logger import logger
from models import TradeAction, AccountInfo, Position, OHLCV


class MT5Service:
    """Service for interacting with MetaTrader 5."""
    
    def __init__(self):
        """Initialize MT5 service."""
        self.connected = False
        self.mock_mode = settings.MOCK_TRADING or not MT5_AVAILABLE
        
        if self.mock_mode:
            logger.info("MT5 running in MOCK MODE - no real trades will be executed")
        else:
            logger.info("MT5 running in LIVE MODE - real trades will be executed")
    
    async def connect(self) -> bool:
        """
        Connect to MetaTrader 5.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self.mock_mode:
            logger.info("Mock mode: Simulating MT5 connection")
            self.connected = True
            return True
        
        if not MT5_AVAILABLE:
            logger.error("MetaTrader5 package not available")
            return False
        
        try:
            # Initialize MT5
            if not mt5.initialize(
                login=settings.MT5_LOGIN,
                password=settings.MT5_PASSWORD,
                server=settings.MT5_SERVER,
                path=settings.MT5_PATH
            ):
                error = mt5.last_error()
                logger.error(f"MT5 initialization failed: {error}")
                return False
            
            self.connected = True
            logger.info(f"MT5 connected successfully - Login: {settings.MT5_LOGIN}")
            
            # Get account info
            account_info = self.get_account_info()
            if account_info:
                logger.info(f"Account Balance: {account_info.balance} {account_info.currency}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to MT5: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from MetaTrader 5."""
        if self.mock_mode:
            logger.info("Mock mode: Simulating MT5 disconnection")
            self.connected = False
            return
        
        if self.connected:
            mt5.shutdown()
            self.connected = False
            logger.info("MT5 disconnected")
    
    def is_connected(self) -> bool:
        """Check if MT5 is connected."""
        return self.connected
    
    def get_account_info(self) -> Optional[AccountInfo]:
        """
        Get account information.
        
        Returns:
            AccountInfo object or None
        """
        if self.mock_mode:
            # Return mock account info
            return AccountInfo(
                login=settings.MT5_LOGIN or 12345678,
                balance=10000.0,
                equity=10000.0,
                margin=0.0,
                free_margin=10000.0,
                profit=0.0,
                leverage=100,
                currency="USD",
                server="Demo-Server"
            )
        
        if not self.connected:
            logger.warning("MT5 not connected")
            return None
        
        try:
            account = mt5.account_info()
            if account is None:
                return None
            
            return AccountInfo(
                login=account.login,
                balance=account.balance,
                equity=account.equity,
                margin=account.margin,
                free_margin=account.margin_free,
                profit=account.profit,
                leverage=account.leverage,
                currency=account.currency,
                server=account.server
            )
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return None
    
    def get_open_positions(self) -> List[Position]:
        """
        Get all open positions.
        
        Returns:
            List of Position objects
        """
        if self.mock_mode:
            # Return empty list in mock mode
            return []
        
        if not self.connected:
            logger.warning("MT5 not connected")
            return []
        
        try:
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            return [
                Position(
                    ticket=pos.ticket,
                    symbol=pos.symbol,
                    type=TradeAction.BUY if pos.type == 0 else TradeAction.SELL,
                    volume=pos.volume,
                    price_open=pos.price_open,
                    price_current=pos.price_current,
                    sl=pos.sl,
                    tp=pos.tp,
                    profit=pos.profit,
                    time=datetime.fromtimestamp(pos.time)
                )
                for pos in positions
            ]
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_historical_data(self, symbol: str, timeframe: str = "M1", 
                           bars: int = 500) -> Optional[pd.DataFrame]:
        """
        Get historical price data.
        
        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1)
            bars: Number of bars to retrieve
            
        Returns:
            DataFrame with OHLCV data
        """
        if self.mock_mode:
            return self._generate_mock_data(symbol, bars)
        
        if not self.connected:
            logger.warning("MT5 not connected")
            return None
        
        try:
            # Map timeframe string to MT5 constant
            timeframe_map = {
                "M1": mt5.TIMEFRAME_M1,
                "M5": mt5.TIMEFRAME_M5,
                "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30,
                "H1": mt5.TIMEFRAME_H1,
                "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            
            tf = timeframe_map.get(timeframe, mt5.TIMEFRAME_M1)
            
            # Get rates
            rates = mt5.copy_rates_from_pos(symbol, tf, 0, bars)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data received for {symbol}")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            df.set_index('time', inplace=True)
            df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume'
            }, inplace=True)
            
            return df[['open', 'high', 'low', 'close', 'volume']]
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return None
    
    def _generate_mock_data(self, symbol: str, bars: int = 500) -> pd.DataFrame:
        """Generate mock price data for testing."""
        import numpy as np
        
        # Generate realistic-looking price data based on symbol
        base_prices = {
            "EURUSD": 1.0850,
            "GBPUSD": 1.2650,
            "USDJPY": 149.50,
            "USDCHF": 0.8850,
            "AUDUSD": 0.6550,
            "USDCAD": 1.3550,
            "XAUUSD": 2035.00  # Gold
        }
        
        base_price = base_prices.get(symbol, 1.0000)
        
        # Generate random walk with slight upward bias
        np.random.seed(hash(symbol) % 2**32)  # Reproducible per symbol
        returns = np.random.normal(0.0001, 0.0005, bars)
        prices = base_price * np.cumprod(1 + returns)
        
        # Generate OHLCV
        data = []
        for i in range(bars):
            close = prices[i]
            daily_range = abs(np.random.normal(0, 0.0003)) * base_price
            high = close + np.random.uniform(0, daily_range)
            low = close - np.random.uniform(0, daily_range)
            open_price = low + np.random.uniform(0, high - low)
            volume = int(np.random.uniform(100, 1000))
            
            data.append({
                'open': open_price,
                'high': high,
                'low': low,
                'close': close,
                'volume': volume
            })
        
        # Create DataFrame with datetime index
        dates = pd.date_range(end=datetime.now(), periods=bars, freq='1min')
        df = pd.DataFrame(data, index=dates)
        
        return df
    
    def place_order(self, symbol: str, action: TradeAction, lot_size: float,
                   stop_loss: Optional[float] = None, 
                   take_profit: Optional[float] = None) -> Optional[int]:
        """
        Place a trade order.
        
        Args:
            symbol: Trading symbol
            action: BUY or SELL
            lot_size: Trade volume in lots
            stop_loss: Stop loss price
            take_profit: Take profit price
            
        Returns:
            Order ticket if successful, None otherwise
        """
        if self.mock_mode:
            logger.info(f"MOCK ORDER: {action.value} {lot_size} lots of {symbol} @ SL:{stop_loss} TP:{take_profit}")
            # Return mock ticket number
            return 123456789
        
        if not self.connected:
            logger.error("MT5 not connected")
            return None
        
        try:
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                logger.error(f"Cannot get price for {symbol}")
                return None
            
            # Determine order type and price
            if action == TradeAction.BUY:
                order_type = mt5.ORDER_TYPE_BUY
                price = tick.ask
            else:
                order_type = mt5.ORDER_TYPE_SELL
                price = tick.bid
            
            # Prepare order request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot_size,
                "type": order_type,
                "price": price,
                "deviation": 10,
                "magic": 234000,
                "comment": "AI Forex Bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Add SL and TP if provided
            if stop_loss:
                request["sl"] = stop_loss
            if take_profit:
                request["tp"] = take_profit
            
            # Send order
            result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error = mt5.last_error()
                logger.error(f"Order failed: {error}")
                return None
            
            logger.info(f"Order placed successfully: Ticket {result.order}")
            return result.order
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None
    
    def close_position(self, ticket: int) -> bool:
        """
        Close an open position.
        
        Args:
            ticket: Position ticket number
            
        Returns:
            True if successful, False otherwise
        """
        if self.mock_mode:
            logger.info(f"MOCK CLOSE: Closing position {ticket}")
            return True
        
        if not self.connected:
            logger.error("MT5 not connected")
            return False
        
        try:
            # Get position info
            position = mt5.positions_get(ticket=ticket)
            if position is None or len(position) == 0:
                logger.error(f"Position {ticket} not found")
                return False
            
            position = position[0]
            
            # Prepare close order (opposite of position type)
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
            else:
                order_type = mt5.ORDER_TYPE_BUY
            
            # Get current price
            tick = mt5.symbol_info_tick(position.symbol)
            if tick is None:
                return False
            
            price = tick.bid if order_type == mt5.ORDER_TYPE_SELL else tick.ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": position.volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": 10,
                "magic": 234000,
                "comment": "Close position",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            
            if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
                error = mt5.last_error()
                logger.error(f"Close order failed: {error}")
                return False
            
            logger.info(f"Position {ticket} closed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return False
    
    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information."""
        if self.mock_mode:
            return {
                "name": symbol,
                "visible": True,
                "trade_mode": 0,
                "spread": 10,
                "digits": 5,
                "volume_min": 0.01,
                "volume_max": 100.0,
                "volume_step": 0.01,
            }
        
        if not self.connected:
            return None
        
        try:
            info = mt5.symbol_info(symbol)
            if info is None:
                return None
            
            return {
                "name": info.name,
                "visible": info.visible,
                "trade_mode": info.trade_mode,
                "spread": info.spread,
                "digits": info.digits,
                "volume_min": info.volume_min,
                "volume_max": info.volume_max,
                "volume_step": info.volume_step,
            }
        except Exception as e:
            logger.error(f"Error getting symbol info: {e}")
            return None
    
    def calculate_pips(self, symbol: str, price_diff: float) -> float:
        """
        Calculate pip value from price difference.
        
        Args:
            symbol: Trading symbol
            price_diff: Price difference
            
        Returns:
            Pip value
        """
        # Standard pip calculation
        if "JPY" in symbol:
            return price_diff * 100
        else:
            return price_diff * 10000
    
    def pips_to_price(self, symbol: str, pips: float) -> float:
        """
        Convert pips to price value.
        
        Args:
            symbol: Trading symbol
            pips: Number of pips
            
        Returns:
            Price value
        """
        if "JPY" in symbol:
            return pips / 100
        else:
            return pips / 10000


# Global service instance
mt5_service = MT5Service()
