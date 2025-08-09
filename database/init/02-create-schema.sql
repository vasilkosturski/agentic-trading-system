-- Agentic Trading System - PostgreSQL Schema Migration
-- Version 1.0 - Initial schema creation with proper normalization

-- Create schemas
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS agents;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- =============================================================================
-- AGENTS SCHEMA - Agent management and logging
-- =============================================================================

-- Trading Agents table
CREATE TABLE agents.trading_agents (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    risk_tolerance DECIMAL(5,2),
    max_position_size DECIMAL(15,2),
    trading_frequency VARCHAR(20) CHECK (trading_frequency IN ('DAILY', 'WEEKLY', 'MONTHLY', 'INTRADAY')),
    preferred_sectors TEXT, -- JSON array
    last_activity TIMESTAMP,
    total_trades INTEGER DEFAULT 0,
    successful_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(15,2) DEFAULT 0.0,
    win_rate DECIMAL(5,2) DEFAULT 0.0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Agent logs table
CREATE TABLE agents.agent_logs (
    id BIGSERIAL PRIMARY KEY,
    agent_name VARCHAR(100) NOT NULL,
    log_datetime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    log_type VARCHAR(50) NOT NULL,
    log_message TEXT,
    log_level VARCHAR(10) NOT NULL DEFAULT 'INFO' CHECK (log_level IN ('DEBUG', 'INFO', 'WARN', 'ERROR')),
    session_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- TRADING SCHEMA - Core trading data
-- =============================================================================

-- Trading accounts table
CREATE TABLE trading.trading_accounts (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    balance DECIMAL(15,2) NOT NULL,
    strategy VARCHAR(100) NOT NULL,
    agent_id BIGINT REFERENCES agents.trading_agents(id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN NOT NULL DEFAULT true
);

-- Account transactions table
CREATE TABLE trading.account_transactions (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES trading.trading_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    price DECIMAL(15,2) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    rationale TEXT,
    transaction_type VARCHAR(10) NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
    total_amount DECIMAL(15,2) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Account holdings table
CREATE TABLE trading.account_holdings (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES trading.trading_accounts(id) ON DELETE CASCADE,
    symbol VARCHAR(20) NOT NULL,
    quantity INTEGER NOT NULL,
    average_price DECIMAL(15,2),
    current_price DECIMAL(15,2),
    market_value DECIMAL(15,2),
    unrealized_pnl DECIMAL(15,2),
    last_updated TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, symbol)
);

-- Account portfolio snapshots table
CREATE TABLE trading.account_portfolio_snapshots (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES trading.trading_accounts(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    total_value DECIMAL(15,2) NOT NULL,
    cash_balance DECIMAL(15,2) NOT NULL,
    holdings_value DECIMAL(15,2) NOT NULL,
    total_pnl DECIMAL(15,2),
    daily_pnl DECIMAL(15,2),
    total_return_percent DECIMAL(10,4),
    snapshot_type VARCHAR(20) NOT NULL CHECK (snapshot_type IN ('DAILY', 'HOURLY', 'TRANSACTION', 'MANUAL')),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Market data table
CREATE TABLE trading.market_data (
    id BIGSERIAL PRIMARY KEY,
    market_date DATE UNIQUE NOT NULL,
    data_json JSONB,
    data_source VARCHAR(50) DEFAULT 'UNKNOWN',
    symbols_count INTEGER,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- ANALYTICS SCHEMA - Analytics and reporting
-- =============================================================================

-- Performance metrics table
CREATE TABLE analytics.performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES trading.trading_accounts(id),
    metric_date DATE NOT NULL,
    total_return DECIMAL(10,4),
    daily_return DECIMAL(10,4),
    volatility DECIMAL(10,4),
    sharpe_ratio DECIMAL(10,4),
    max_drawdown DECIMAL(10,4),
    win_rate DECIMAL(5,2),
    profit_factor DECIMAL(10,4),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(account_id, metric_date)
);

-- Risk metrics table
CREATE TABLE analytics.risk_metrics (
    id BIGSERIAL PRIMARY KEY,
    account_id BIGINT NOT NULL REFERENCES trading.trading_accounts(id),
    calculated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    var_95 DECIMAL(15,2), -- Value at Risk 95%
    var_99 DECIMAL(15,2), -- Value at Risk 99%
    beta DECIMAL(10,4),
    correlation_spy DECIMAL(10,4),
    portfolio_concentration DECIMAL(5,2),
    sector_exposure JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================================
-- INDEXES for performance optimization
-- =============================================================================

-- Agents schema indexes
CREATE INDEX idx_trading_agents_name ON agents.trading_agents(name);
CREATE INDEX idx_trading_agents_strategy ON agents.trading_agents(strategy);
CREATE INDEX idx_trading_agents_active ON agents.trading_agents(is_active);
CREATE INDEX idx_agent_logs_agent_name ON agents.agent_logs(agent_name);
CREATE INDEX idx_agent_logs_datetime ON agents.agent_logs(log_datetime);
CREATE INDEX idx_agent_logs_level ON agents.agent_logs(log_level);

-- Trading schema indexes
CREATE INDEX idx_trading_accounts_name ON trading.trading_accounts(name);
CREATE INDEX idx_trading_accounts_agent ON trading.trading_accounts(agent_id);
CREATE INDEX idx_account_transactions_account ON trading.account_transactions(account_id);
CREATE INDEX idx_account_transactions_symbol ON trading.account_transactions(symbol);
CREATE INDEX idx_account_transactions_timestamp ON trading.account_transactions(timestamp);
CREATE INDEX idx_account_holdings_account ON trading.account_holdings(account_id);
CREATE INDEX idx_account_holdings_symbol ON trading.account_holdings(symbol);
CREATE INDEX idx_portfolio_snapshots_account ON trading.account_portfolio_snapshots(account_id);
CREATE INDEX idx_portfolio_snapshots_timestamp ON trading.account_portfolio_snapshots(timestamp);
CREATE INDEX idx_market_data_date ON trading.market_data(market_date);
CREATE INDEX idx_market_data_source ON trading.market_data(data_source);

-- Analytics schema indexes
CREATE INDEX idx_performance_metrics_account ON analytics.performance_metrics(account_id);
CREATE INDEX idx_performance_metrics_date ON analytics.performance_metrics(metric_date);
CREATE INDEX idx_risk_metrics_account ON analytics.risk_metrics(account_id);
CREATE INDEX idx_risk_metrics_calculated ON analytics.risk_metrics(calculated_at);

-- JSONB indexes for market data
CREATE INDEX idx_market_data_json ON trading.market_data USING GIN (data_json);

-- Full-text search indexes
CREATE INDEX idx_agent_logs_message_fts ON agents.agent_logs USING GIN (to_tsvector('english', log_message));

-- =============================================================================
-- TRIGGERS for automatic timestamp updates
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers to tables with updated_at columns
CREATE TRIGGER update_trading_agents_updated_at 
    BEFORE UPDATE ON agents.trading_agents 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trading_accounts_updated_at 
    BEFORE UPDATE ON trading.trading_accounts 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_market_data_updated_at 
    BEFORE UPDATE ON trading.market_data 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- VIEWS for common queries
-- =============================================================================

-- Active trading accounts with agent information
CREATE VIEW trading.active_accounts_with_agents AS
SELECT 
    ta.id,
    ta.name,
    ta.balance,
    ta.strategy,
    ta.created_at,
    ta.updated_at,
    ag.name as agent_name,
    ag.win_rate as agent_win_rate,
    ag.total_pnl as agent_total_pnl,
    ag.last_activity as agent_last_activity
FROM trading.trading_accounts ta
LEFT JOIN agents.trading_agents ag ON ta.agent_id = ag.id
WHERE ta.is_active = true;

-- Portfolio summary view
CREATE VIEW trading.portfolio_summary AS
SELECT 
    ta.id as account_id,
    ta.name as account_name,
    ta.balance,
    COUNT(ah.id) as total_positions,
    SUM(ah.market_value) as total_holdings_value,
    SUM(ah.unrealized_pnl) as total_unrealized_pnl,
    ta.balance + COALESCE(SUM(ah.market_value), 0) as total_portfolio_value
FROM trading.trading_accounts ta
LEFT JOIN trading.account_holdings ah ON ta.id = ah.account_id AND ah.quantity > 0
WHERE ta.is_active = true
GROUP BY ta.id, ta.name, ta.balance;

-- Recent transactions view
CREATE VIEW trading.recent_transactions AS
SELECT 
    at.id,
    ta.name as account_name,
    at.symbol,
    at.quantity,
    at.price,
    at.total_amount,
    at.transaction_type,
    at.timestamp,
    at.rationale
FROM trading.account_transactions at
JOIN trading.trading_accounts ta ON at.account_id = ta.id
WHERE at.timestamp >= CURRENT_DATE - INTERVAL '30 days'
ORDER BY at.timestamp DESC;

-- =============================================================================
-- GRANTS and PERMISSIONS
-- =============================================================================

-- Grant usage on schemas
GRANT USAGE ON SCHEMA trading TO trading_user;
GRANT USAGE ON SCHEMA agents TO trading_user;
GRANT USAGE ON SCHEMA analytics TO trading_user;

-- Grant table permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA trading TO trading_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA agents TO trading_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA analytics TO trading_user;

-- Grant sequence permissions
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA trading TO trading_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA agents TO trading_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO trading_user;

-- Grant view permissions
GRANT SELECT ON ALL TABLES IN SCHEMA trading TO trading_user;

-- =============================================================================
-- SAMPLE DATA for testing
-- =============================================================================

-- Insert sample trading agents
INSERT INTO agents.trading_agents (name, strategy, description, risk_tolerance, trading_frequency) VALUES
('warren', 'Value Investing', 'Long-term value investor focused on undervalued companies', 0.3, 'WEEKLY'),
('george', 'Momentum Trading', 'Short-term momentum trader focusing on technical analysis', 0.7, 'DAILY'),
('ray', 'Diversified Portfolio', 'Balanced approach with risk management focus', 0.5, 'MONTHLY'),
('cathie', 'Growth Investing', 'Innovation-focused growth investor', 0.8, 'WEEKLY');

-- Insert sample trading accounts
INSERT INTO trading.trading_accounts (name, balance, strategy, agent_id) VALUES
('warren', 100000.00, 'Value Investing', 1),
('george', 50000.00, 'Momentum Trading', 2),
('ray', 75000.00, 'Diversified Portfolio', 3),
('cathie', 60000.00, 'Growth Investing', 4);

-- Insert sample log entries
INSERT INTO agents.agent_logs (agent_name, log_type, log_message, log_level) VALUES
('warren', 'STARTUP', 'Agent initialized successfully', 'INFO'),
('george', 'STARTUP', 'Agent initialized successfully', 'INFO'),
('ray', 'STARTUP', 'Agent initialized successfully', 'INFO'),
('cathie', 'STARTUP', 'Agent initialized successfully', 'INFO');

COMMIT;