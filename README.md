# AI Forex Trading Bot - Setup Instructions

## 📋 Prerequisites

- Python 3.9 or higher
- Supabase account (free tier available)
- MetaTrader 5 (Windows only, for live trading)
- pip (Python package manager)

---

## 🚀 Quick Start Guide

### Step 1: Clone and Setup Environment

```bash
cd /workspace

# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn pandas numpy ta python-dotenv pydantic websockets aiohttp supabase
```

### Step 2: Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your credentials
# Required settings:
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key

# Optional MT5 settings (for mock mode, these can be dummy values)
MT5_LOGIN=12345678
MT5_PASSWORD=your_password
MT5_SERVER=your_broker_server

# Set MOCK_TRADING=true for testing without real trades
MOCK_TRADING=true
```

### Step 3: Setup Supabase Database

1. Go to [Supabase](https://supabase.com) and create a new project
2. Navigate to SQL Editor in your Supabase dashboard
3. Copy and paste the contents of `supabase_schema.sql`
4. Run the SQL to create all tables, indexes, and policies

### Step 4: Run the Application

```bash
# Start the FastAPI server
python main.py

# Or using uvicorn directly:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`
API Documentation: `http://localhost:8000/docs`

### Step 5: Open the Frontend

Open `frontend/index.html` in your browser, or serve it with a simple HTTP server:

```bash
# Using Python
cd frontend
python -m http.server 3000

# Then open: http://localhost:3000
```

---

## 📁 Project Structure

```
/workspace
├── main.py                 # FastAPI application entry point
├── config/
│   └── settings.py         # Configuration management
├── models/
│   └── __init__.py         # Pydantic data models
├── routes/
│   ├── chat.py             # Chat endpoints
│   ├── trade.py            # Trading endpoints
│   └── auth.py             # Authentication endpoints
├── services/
│   ├── mt5_service.py      # MetaTrader 5 integration
│   ├── supabase_service.py # Database operations
│   ├── strategy.py         # Trading strategy logic
│   ├── risk_manager.py     # Risk management rules
│   └── ai_engine.py        # Chat intent parsing
├── utils/
│   ├── indicators.py       # Technical indicators
│   └── logger.py           # Logging configuration
├── frontend/
│   └── index.html          # Chat UI
├── tests/                  # Test files
├── logs/                   # Application logs (auto-created)
├── .env.example            # Environment template
├── .env                    # Your configuration (create from example)
└── supabase_schema.sql     # Database schema
```

---

## 🔧 Configuration Options

### Trading Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_RISK_PERCENT` | 2.0 | Maximum risk per trade (%) |
| `MAX_TRADES_PER_DAY` | 3 | Maximum trades per day |
| `DEFAULT_LOT_SIZE` | 0.01 | Default trade size |
| `DEFAULT_STOP_LOSS_PIPS` | 50 | Default stop loss in pips |
| `DEFAULT_TAKE_PROFIT_PIPS` | 100 | Default take profit in pips |

### Mock Mode

Set `MOCK_TRADING=true` to run without real MT5 connection. The bot will:
- Generate simulated market data
- Simulate order execution
- Log all actions without real trades

**Recommended for testing!**

---

## 📡 API Endpoints

### Chat
- `POST /chat` - Send message to bot
- `GET /chat/history` - Get chat history
- `GET /chat/auto-trade/status` - Get auto-trading status
- `POST /chat/auto-trade/start` - Start auto-trading
- `POST /chat/auto-trade/stop` - Stop auto-trading

### Trading
- `POST /trade` - Execute manual trade
- `POST /trade/close/{ticket}` - Close position
- `GET /trade/positions` - Get open positions
- `GET /trade/history` - Get trade history
- `GET /trade/statistics` - Get trading stats
- `GET /trade/analysis/{symbol}` - Get market analysis

### Auth
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login
- `GET /auth/me` - Get current user

### Status
- `GET /` - API info
- `GET /status` - Bot status

---

## 💬 Example Chat Commands

```
Buy EURUSD
Sell GBPUSD 0.1 lots
What is the trend?
Start auto trading
Stop auto trading
Show my trades
Account balance
Any signals?
Help
```

---

## 🧪 Testing

### Test the API with curl

```bash
# Check status
curl http://localhost:8000/status

# Send chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Buy EURUSD"}'

# Get market analysis
curl http://localhost:8000/trade/analysis/EURUSD

# Start auto-trading
curl -X POST http://localhost:8000/chat/auto-trade/start
```

---

## ⚠️ Important Notes

### For Live Trading

1. **Disable Mock Mode**: Set `MOCK_TRADING=false`
2. **Install MT5**: MetaTrader 5 is Windows-only
3. **Configure MT5**: Add your broker credentials to `.env`
4. **Test on Demo**: Always test on demo account first!

### Risk Warning

- This software is for educational purposes
- Forex trading involves significant risk
- Never trade money you cannot afford to lose
- Past performance does not guarantee future results

---

## 🔍 Troubleshooting

### Common Issues

**"Module not found" errors:**
```bash
pip install -r requirements.txt
```

**Supabase connection failed:**
- Verify SUPABASE_URL and SUPABASE_KEY in `.env`
- Check that tables are created in Supabase

**MT5 not connecting:**
- Ensure MT5 is installed (Windows only)
- Check credentials in `.env`
- Set `MOCK_TRADING=true` for testing without MT5

**Port already in use:**
```bash
# Change port in .env or run with different port
uvicorn main:app --port 8001
```

---

## 📊 Monitoring

View application logs:
```bash
tail -f logs/forex_bot_*.log
```

Check API documentation:
```
http://localhost:8000/docs
```

---

## 🎯 Next Steps

1. **Customize Strategy**: Edit `services/strategy.py` to modify trading logic
2. **Add Indicators**: Extend `utils/indicators.py` with new technical indicators
3. **Improve AI**: Enhance `services/ai_engine.py` with ML models
4. **Deploy**: Deploy to cloud provider (AWS, GCP, Azure)
5. **Add WebSocket**: Implement real-time updates

---

## 📞 Support

For issues and questions:
1. Check the logs in `/logs` directory
2. Review API docs at `/docs`
3. Enable debug mode: `DEBUG=true` in `.env`

---

**Happy Trading! 🚀📈**
