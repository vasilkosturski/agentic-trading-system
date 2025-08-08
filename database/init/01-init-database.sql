-- PostgreSQL Database Initialization Script
-- This script sets up the initial database structure and permissions

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schemas for better organization
CREATE SCHEMA IF NOT EXISTS trading;
CREATE SCHEMA IF NOT EXISTS agents;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant permissions to trading_user
GRANT USAGE ON SCHEMA trading TO trading_user;
GRANT USAGE ON SCHEMA agents TO trading_user;
GRANT USAGE ON SCHEMA analytics TO trading_user;

GRANT CREATE ON SCHEMA trading TO trading_user;
GRANT CREATE ON SCHEMA agents TO trading_user;
GRANT CREATE ON SCHEMA analytics TO trading_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA trading GRANT ALL ON TABLES TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA agents GRANT ALL ON TABLES TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT ALL ON TABLES TO trading_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA trading GRANT ALL ON SEQUENCES TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA agents GRANT ALL ON SEQUENCES TO trading_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT ALL ON SEQUENCES TO trading_user;

-- Create indexes for better performance (will be created by Hibernate, but good to have)
-- Note: Actual table creation will be handled by Hibernate JPA

-- Log the initialization
INSERT INTO pg_stat_statements_info (dealloc) VALUES (0) ON CONFLICT DO NOTHING;

-- Create a simple health check function
CREATE OR REPLACE FUNCTION health_check()
RETURNS TEXT AS $$
BEGIN
    RETURN 'PostgreSQL is healthy - ' || NOW()::TEXT;
END;
$$ LANGUAGE plpgsql;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Agentic Trading System database initialized successfully at %', NOW();
END $$;