-- Supabase Schema for AI Forex Trading Bot
-- Run this SQL in your Supabase SQL Editor to create the required tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Trades table
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('BUY', 'SELL', 'CLOSE')),
    lot_size DECIMAL(10, 2) NOT NULL,
    entry_price DECIMAL(18, 8),
    stop_loss DECIMAL(18, 8),
    take_profit DECIMAL(18, 8),
    close_price DECIMAL(18, 8),
    profit DECIMAL(18, 2),
    status VARCHAR(20) DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'OPEN', 'CLOSED', 'CANCELLED', 'REJECTED')),
    mt5_order_id BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    closed_at TIMESTAMP WITH TIME ZONE,
    notes TEXT
);

-- Signals table
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    signal_type VARCHAR(10) NOT NULL CHECK (signal_type IN ('BUY', 'SELL', 'HOLD')),
    strength DECIMAL(5, 2) DEFAULT 0,
    price DECIMAL(18, 8) NOT NULL,
    ema_50 DECIMAL(18, 8),
    ema_200 DECIMAL(18, 8),
    rsi DECIMAL(5, 2),
    reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    executed BOOLEAN DEFAULT FALSE,
    trade_id UUID REFERENCES trades(id)
);

-- Chat logs table
CREATE TABLE chat_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    response TEXT,
    intent VARCHAR(50),
    action VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Settings table
CREATE TABLE settings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

-- Create indexes for better query performance
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_status ON trades(status);
CREATE INDEX idx_trades_created_at ON trades(created_at);
CREATE INDEX idx_signals_user_id ON signals(user_id);
CREATE INDEX idx_signals_signal_type ON signals(signal_type);
CREATE INDEX idx_chat_logs_user_id ON chat_logs(user_id);
CREATE INDEX idx_chat_logs_created_at ON chat_logs(created_at);

-- Row Level Security (RLS) Policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- Users can only view their own data
CREATE POLICY "Users can view own data" ON users
    FOR SELECT
    USING (auth.uid() = id OR id::text = current_setting('app.current_user_id', true));

CREATE POLICY "Users can view own trades" ON trades
    FOR SELECT
    USING (user_id::text = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own trades" ON trades
    FOR INSERT
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

CREATE POLICY "Users can update own trades" ON trades
    FOR UPDATE
    USING (user_id::text = current_setting('app.current_user_id', true));

CREATE POLICY "Users can view own signals" ON signals
    FOR SELECT
    USING (user_id::text = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own signals" ON signals
    FOR INSERT
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

CREATE POLICY "Users can view own chat logs" ON chat_logs
    FOR SELECT
    USING (user_id::text = current_setting('app.current_user_id', true));

CREATE POLICY "Users can insert own chat logs" ON chat_logs
    FOR INSERT
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

CREATE POLICY "Users can view own settings" ON settings
    FOR SELECT
    USING (user_id::text = current_setting('app.current_user_id', true));

CREATE POLICY "Users can upsert own settings" ON settings
    FOR ALL
    USING (user_id::text = current_setting('app.current_user_id', true))
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

-- Function to get trade statistics
CREATE OR REPLACE FUNCTION get_trade_stats(p_user_id UUID)
RETURNS TABLE (
    total_trades BIGINT,
    winning_trades BIGINT,
    losing_trades BIGINT,
    win_rate DECIMAL,
    total_profit DECIMAL,
    average_profit DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*)::BIGINT as total_trades,
        COUNT(CASE WHEN profit > 0 THEN 1 END)::BIGINT as winning_trades,
        COUNT(CASE WHEN profit <= 0 THEN 1 END)::BIGINT as losing_trades,
        ROUND(
            COUNT(CASE WHEN profit > 0 THEN 1 END)::DECIMAL / 
            NULLIF(COUNT(*), 0) * 100, 2
        ) as win_rate,
        COALESCE(SUM(profit), 0)::DECIMAL as total_profit,
        COALESCE(AVG(profit), 0)::DECIMAL as average_profit
    FROM trades
    WHERE user_id = p_user_id 
    AND status = 'CLOSED';
END;
$$ LANGUAGE plpgsql;

-- Function to get trades count for today
CREATE OR REPLACE FUNCTION get_trades_today_count(p_user_id UUID)
RETURNS INTEGER AS $$
BEGIN
    RETURN (
        SELECT COUNT(*)
        FROM trades
        WHERE user_id = p_user_id
        AND DATE(created_at) = CURRENT_DATE
        AND status IN ('OPEN', 'CLOSED')
    );
END;
$$ LANGUAGE plpgsql;

-- Insert sample data (optional - for testing)
-- Uncomment to add test data
/*
INSERT INTO users (id, email) VALUES 
    ('00000000-0000-0000-0000-000000000001', 'test@example.com');

INSERT INTO trades (user_id, symbol, action, lot_size, entry_price, stop_loss, take_profit, status) VALUES
    ('00000000-0000-0000-0000-000000000001', 'EURUSD', 'BUY', 0.01, 1.0850, 1.0800, 1.0950, 'CLOSED'),
    ('00000000-0000-0000-0000-000000000001', 'GBPUSD', 'SELL', 0.01, 1.2650, 1.2700, 1.2550, 'CLOSED');
*/
