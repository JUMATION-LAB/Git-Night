"""
AI Chat Engine for the AI Forex Trading Bot.
Parses user intent and generates intelligent responses.
"""
import re
from typing import Dict, Any, Optional, List
from datetime import datetime

from utils.logger import logger
from models import ChatResponse, TradeAction, SignalType


class AIChatEngine:
    """
    AI chat engine for parsing user intent and generating responses.
    
    Supports commands like:
    - "Buy EURUSD"
    - "Sell GBPUSD 0.1 lots"
    - "Start auto trading"
    - "Stop trading"
    - "What is the trend?"
    - "Show my trades"
    - "Close position EURUSD"
    """
    
    def __init__(self):
        """Initialize chat engine."""
        # Intent patterns
        self.patterns = {
            'buy': r'\b(buy|long|go long|open buy)\b',
            'sell': r'\b(sell|short|go short|open sell)\b',
            'close': r'\b(close|exit|shutdown)\b',
            'auto_trade_start': r'\b(start|enable|activate|turn on)\b.*\b(auto|bot)\b',
            'auto_trade_stop': r'\b(stop|disable|deactivate|turn off)\b.*\b(auto|bot)\b',
            'trend': r'\b(trend|market direction|market sentiment)\b',
            'show_trades': r'\b(my trades|open positions|positions|trade history)\b',
            'account': r'\b(account|balance|equity|portfolio)\b',
            'signal': r'\b(signal|recommendation|what should i do)\b',
            'help': r'\b(help|commands|what can you do)\b',
            'status': r'\b(status|bot status|are you running)\b',
            'stop_loss': r'\b(set\s+stop\s*loss|stop\s*loss|sl)\b',
            'take_profit': r'\b(take\s*profit|tp|target)\b',
        }
        
        # Symbol patterns
        self.symbol_pattern = r'\b([A-Z]{6}|[A-Z]{3}USD|[XAU|xau][A-Z]{2}|[A-Z]{2}[XAU|xau])\b'
        
        # Lot size pattern
        self.lot_pattern = r'(\d+\.?\d*)\s*(lot|lots|volume)'
        
        # Numbers for SL/TP
        self.number_pattern = r'(\d+\.?\d*)'
    
    def parse_message(self, message: str) -> Dict[str, Any]:
        """
        Parse user message and extract intent.
        
        Args:
            message: User message
            
        Returns:
            Dictionary with parsed intent and parameters
        """
        message_lower = message.lower().strip()
        
        result = {
            'intent': None,
            'action': None,
            'symbol': None,
            'lot_size': None,
            'stop_loss': None,
            'take_profit': None,
            'confidence': 0.0
        }
        
        # Extract symbol
        symbol_match = re.search(self.symbol_pattern, message, re.IGNORECASE)
        if symbol_match:
            result['symbol'] = symbol_match.group(1).upper()
        
        # Extract lot size
        lot_match = re.search(self.lot_pattern, message_lower)
        if lot_match:
            try:
                result['lot_size'] = float(lot_match.group(1))
            except ValueError:
                pass
        
        # Detect intent
        for intent, pattern in self.patterns.items():
            if re.search(pattern, message_lower):
                result['intent'] = intent
                result['confidence'] = 0.8
                
                # Map intent to action
                if intent == 'buy':
                    result['action'] = TradeAction.BUY.value
                elif intent == 'sell':
                    result['action'] = TradeAction.SELL.value
                elif intent == 'close':
                    result['action'] = 'CLOSE_POSITION'
                elif intent in ['auto_trade_start']:
                    result['action'] = 'START_AUTO_TRADE'
                elif intent in ['auto_trade_stop']:
                    result['action'] = 'STOP_AUTO_TRADE'
                elif intent in ['trend', 'signal']:
                    result['action'] = 'GET_ANALYSIS'
                elif intent == 'show_trades':
                    result['action'] = 'SHOW_TRADES'
                elif intent == 'account':
                    result['action'] = 'SHOW_ACCOUNT'
                elif intent == 'help':
                    result['action'] = 'SHOW_HELP'
                elif intent == 'status':
                    result['action'] = 'SHOW_STATUS'
                
                break
        
        # If no specific intent, check for simple commands
        if result['intent'] is None:
            if result['symbol']:
                # Check if it's a simple "EURUSD" query
                if '?' in message or 'price' in message_lower:
                    result['intent'] = 'price_query'
                    result['action'] = 'GET_PRICE'
                    result['confidence'] = 0.7
        
        return result
    
    def generate_response(self, parsed: Dict[str, Any], 
                         context: Optional[Dict[str, Any]] = None) -> ChatResponse:
        """
        Generate response based on parsed intent and context.
        
        Args:
            parsed: Parsed message data
            context: Additional context (market data, account info, etc.)
            
        Returns:
            ChatResponse object
        """
        intent = parsed.get('intent', 'unknown')
        action = parsed.get('action', 'UNKNOWN')
        symbol = parsed.get('symbol')
        
        # Generate response text
        response_text = self._generate_response_text(intent, action, symbol, context)
        
        return ChatResponse(
            intent=intent or 'unknown',
            action=action or 'UNKNOWN',
            response=response_text,
            data=context
        )
    
    def _generate_response_text(self, intent: str, action: str, 
                               symbol: Optional[str],
                               context: Optional[Dict[str, Any]]) -> str:
        """Generate human-readable response text."""
        
        if intent == 'buy':
            if symbol:
                return f"Ready to execute BUY order for {symbol}. Confirming trade parameters..."
            return "Which symbol would you like to buy? (e.g., EURUSD, GBPUSD)"
        
        elif intent == 'sell':
            if symbol:
                return f"Ready to execute SELL order for {symbol}. Confirming trade parameters..."
            return "Which symbol would you like to sell? (e.g., EURUSD, GBPUSD)"
        
        elif intent == 'close':
            if symbol:
                return f"Closing position for {symbol}..."
            return "Which position would you like to close?"
        
        elif intent == 'auto_trade_start':
            return "Auto-trading has been enabled. The bot will now analyze markets and execute trades automatically."
        
        elif intent == 'auto_trade_stop':
            return "Auto-trading has been disabled. No new trades will be opened automatically."
        
        elif intent == 'trend':
            if context and 'analysis' in context:
                analysis = context['analysis']
                return f"Current trend for {symbol}: {analysis.get('trend', 'Unknown')}. " \
                       f"RSI: {analysis.get('indicators', {}).get('rsi', 'N/A'):.1f}. " \
                       f"Signal: {analysis.get('signal', {}).get('type', 'HOLD')}"
            if symbol:
                return f"Analyzing trend for {symbol}..."
            return "Which symbol would you like me to analyze?"
        
        elif intent == 'show_trades':
            if context and 'trades' in context:
                trades = context['trades']
                if not trades:
                    return "You have no open trades."
                return f"You have {len(trades)} open trade(s). Check your dashboard for details."
            return "Fetching your trades..."
        
        elif intent == 'account':
            if context and 'account' in context:
                acc = context['account']
                return f"Account Balance: ${acc.get('balance', 0):.2f} | " \
                       f"Equity: ${acc.get('equity', 0):.2f} | " \
                       f"Free Margin: ${acc.get('free_margin', 0):.2f}"
            return "Fetching account information..."
        
        elif intent == 'signal':
            if context and 'analysis' in context:
                analysis = context['analysis']
                signal = analysis.get('signal', {})
                if signal.get('type') == 'HOLD':
                    return f"No trading signal at this time. {signal.get('reason', '')}"
                return f"🎯 SIGNAL: {signal.get('type')} {symbol or ''} | " \
                       f"Strength: {signal.get('strength', 0):.0f}% | " \
                       f"{signal.get('reason', '')}"
            return "Analyzing market for signals..."
        
        elif intent == 'help':
            return self._get_help_text()
        
        elif intent == 'status':
            if context and 'status' in context:
                status = context['status']
                if status.get('is_running'):
                    return f"Bot is RUNNING ✅ | Auto-trading: {'ON' if status.get('auto_trading') else 'OFF'} | " \
                           f"Trades today: {status.get('trades_today', 0)}"
                return "Bot is currently STOPPED ❌"
            return "Checking bot status..."
        
        elif action == 'GET_PRICE':
            if symbol:
                if context and 'price' in context:
                    return f"Current price for {symbol}: {context['price']}"
                return f"Fetching price for {symbol}..."
            return "Which symbol's price would you like to know?"
        
        else:
            return "I'm not sure I understand. Type 'help' for available commands."
    
    def _get_help_text(self) -> str:
        """Get help text with available commands."""
        return """
📊 **Available Commands:**

**Trading:**
• `Buy EURUSD` - Open buy position
• `Sell GBPUSD 0.1 lots` - Open sell position
• `Close EURUSD` - Close position
• `Set stop loss 50 pips` - Set stop loss

**Auto-Trading:**
• `Start auto trading` - Enable automatic trading
• `Stop auto trading` - Disable automatic trading

**Analysis:**
• `What is the trend?` - Get market analysis
• `EURUSD trend` - Get specific symbol analysis
• `Any signals?` - Get trading signals

**Account:**
• `Show my trades` - View open positions
• `Account balance` - View account info
• `Bot status` - Check if bot is running

**Examples:**
• "Buy EURUSD with 0.01 lots"
• "Sell GBPUSD, stop loss 50 pips"
• "What's the trend on Gold?"
        """.strip()
    
    def extract_trade_parameters(self, message: str) -> Dict[str, Any]:
        """
        Extract detailed trade parameters from message.
        
        Args:
            message: User message
            
        Returns:
            Dictionary with trade parameters
        """
        params = {
            'symbol': None,
            'action': None,
            'lot_size': None,
            'stop_loss_pips': None,
            'take_profit_pips': None
        }
        
        message_lower = message.lower()
        
        # Extract symbol
        symbol_match = re.search(self.symbol_pattern, message, re.IGNORECASE)
        if symbol_match:
            params['symbol'] = symbol_match.group(1).upper()
        
        # Determine action
        if re.search(self.patterns['buy'], message_lower):
            params['action'] = 'BUY'
        elif re.search(self.patterns['sell'], message_lower):
            params['action'] = 'SELL'
        
        # Extract lot size
        lot_match = re.search(self.lot_pattern, message_lower)
        if lot_match:
            params['lot_size'] = float(lot_match.group(1))
        
        # Extract stop loss
        sl_match = re.search(r'stop\s*loss\s*(?:of\s*)?(\d+\.?\d*)\s*(?:pips)?', message_lower)
        if sl_match:
            params['stop_loss_pips'] = float(sl_match.group(1))
        
        # Extract take profit
        tp_match = re.search(r'take\s*profit\s*(?:of\s*)?(\d+\.?\d*)\s*(?:pips)?', message_lower)
        if tp_match:
            params['take_profit_pips'] = float(tp_match.group(1))
        
        return params


# Global chat engine instance
ai_chat_engine = AIChatEngine()
