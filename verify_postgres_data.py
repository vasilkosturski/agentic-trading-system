#!/usr/bin/env python3

import asyncio
import asyncpg
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class PostgreSQLVerifier:
    """
    Verifies that trading data is being written to PostgreSQL database
    """
    
    def __init__(self):
        # PostgreSQL connection parameters
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'agentic_trading'),
            'user': os.getenv('POSTGRES_USER', 'trading_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'trading_pass')
        }
    
    async def connect_to_database(self):
        """Connect to PostgreSQL database"""
        try:
            conn = await asyncpg.connect(**self.db_config)
            print(f"✅ Connected to PostgreSQL database: {self.db_config['database']}")
            return conn
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            print(f"🔧 Connection config: {self.db_config}")
            return None
    
    async def verify_database_structure(self, conn):
        """Verify that the expected tables exist"""
        print("\n🔍 VERIFYING DATABASE STRUCTURE")
        print("-" * 50)
        
        # Check for expected tables
        expected_tables = [
            'trading.trading_accounts',
            'trading.account_transactions', 
            'trading.account_holdings',
            'trading.account_portfolio_snapshots',
            'agents.trading_agents'
        ]
        
        for table in expected_tables:
            try:
                result = await conn.fetchval(
                    "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = $1 AND table_name = $2",
                    table.split('.')[0], table.split('.')[1]
                )
                if result > 0:
                    print(f"✅ Table exists: {table}")
                else:
                    print(f"❌ Table missing: {table}")
            except Exception as e:
                print(f"❌ Error checking table {table}: {e}")
    
    async def check_trading_accounts(self, conn):
        """Check trading accounts data"""
        print("\n👥 TRADING ACCOUNTS")
        print("-" * 30)
        
        try:
            accounts = await conn.fetch("""
                SELECT account_name, cash_balance, total_portfolio_value, 
                       created_at, updated_at
                FROM trading.trading_accounts 
                ORDER BY account_name
            """)
            
            if accounts:
                print(f"📊 Found {len(accounts)} trading accounts:")
                for account in accounts:
                    print(f"   👤 {account['account_name']}")
                    print(f"      💰 Cash: ${account['cash_balance']:,.2f}")
                    print(f"      📈 Portfolio: ${account['total_portfolio_value']:,.2f}")
                    print(f"      🕐 Updated: {account['updated_at']}")
                    print()
            else:
                print("❌ No trading accounts found")
                
        except Exception as e:
            print(f"❌ Error checking trading accounts: {e}")
    
    async def check_transactions(self, conn):
        """Check recent transactions"""
        print("\n💸 RECENT TRANSACTIONS")
        print("-" * 30)
        
        try:
            transactions = await conn.fetch("""
                SELECT ta.account_name, at.transaction_type, at.symbol, 
                       at.quantity, at.price_per_share, at.total_amount,
                       at.rationale, at.created_at
                FROM trading.account_transactions at
                JOIN trading.trading_accounts ta ON at.account_id = ta.account_id
                ORDER BY at.created_at DESC
                LIMIT 20
            """)
            
            if transactions:
                print(f"📊 Found {len(transactions)} recent transactions:")
                for tx in transactions:
                    action_emoji = "🟢" if tx['transaction_type'] == 'BUY' else "🔴"
                    print(f"   {action_emoji} {tx['account_name']}: {tx['transaction_type']} {tx['quantity']} {tx['symbol']}")
                    print(f"      💵 ${tx['price_per_share']:.2f}/share = ${tx['total_amount']:,.2f} total")
                    print(f"      💭 {tx['rationale'][:60]}...")
                    print(f"      🕐 {tx['created_at']}")
                    print()
            else:
                print("❌ No transactions found")
                
        except Exception as e:
            print(f"❌ Error checking transactions: {e}")
    
    async def check_holdings(self, conn):
        """Check current holdings"""
        print("\n📊 CURRENT HOLDINGS")
        print("-" * 30)
        
        try:
            holdings = await conn.fetch("""
                SELECT ta.account_name, ah.symbol, ah.quantity, 
                       ah.average_cost_per_share, ah.current_market_value,
                       ah.updated_at
                FROM trading.account_holdings ah
                JOIN trading.trading_accounts ta ON ah.account_id = ta.account_id
                WHERE ah.quantity > 0
                ORDER BY ta.account_name, ah.symbol
            """)
            
            if holdings:
                print(f"📊 Found {len(holdings)} active holdings:")
                current_account = None
                for holding in holdings:
                    if holding['account_name'] != current_account:
                        current_account = holding['account_name']
                        print(f"\n   👤 {current_account}:")
                    
                    total_value = holding['quantity'] * holding['average_cost_per_share']
                    print(f"      📈 {holding['symbol']}: {holding['quantity']} shares")
                    print(f"         💰 Avg Cost: ${holding['average_cost_per_share']:.2f}")
                    print(f"         💵 Total Value: ${total_value:,.2f}")
                    print(f"         🕐 Updated: {holding['updated_at']}")
            else:
                print("❌ No holdings found")
                
        except Exception as e:
            print(f"❌ Error checking holdings: {e}")
    
    async def check_portfolio_snapshots(self, conn):
        """Check portfolio snapshots"""
        print("\n📸 PORTFOLIO SNAPSHOTS")
        print("-" * 30)
        
        try:
            snapshots = await conn.fetch("""
                SELECT ta.account_name, aps.total_cash, aps.total_holdings_value,
                       aps.total_portfolio_value, aps.snapshot_date
                FROM trading.account_portfolio_snapshots aps
                JOIN trading.trading_accounts ta ON aps.account_id = ta.account_id
                ORDER BY aps.snapshot_date DESC
                LIMIT 10
            """)
            
            if snapshots:
                print(f"📊 Found {len(snapshots)} recent snapshots:")
                for snapshot in snapshots:
                    print(f"   📸 {snapshot['account_name']} - {snapshot['snapshot_date']}")
                    print(f"      💰 Cash: ${snapshot['total_cash']:,.2f}")
                    print(f"      📈 Holdings: ${snapshot['total_holdings_value']:,.2f}")
                    print(f"      💵 Total: ${snapshot['total_portfolio_value']:,.2f}")
                    print()
            else:
                print("❌ No portfolio snapshots found")
                
        except Exception as e:
            print(f"❌ Error checking portfolio snapshots: {e}")
    
    async def check_agent_status(self, conn):
        """Check agent status"""
        print("\n🤖 AGENT STATUS")
        print("-" * 30)
        
        try:
            agents = await conn.fetch("""
                SELECT agent_name, agent_type, status, last_activity,
                       current_strategy, risk_tolerance
                FROM agents.trading_agents
                ORDER BY agent_name
            """)
            
            if agents:
                print(f"📊 Found {len(agents)} agents:")
                for agent in agents:
                    status_emoji = "🟢" if agent['status'] == 'ACTIVE' else "🔴"
                    print(f"   {status_emoji} {agent['agent_name']} ({agent['agent_type']})")
                    print(f"      📊 Status: {agent['status']}")
                    print(f"      🎯 Strategy: {agent['current_strategy']}")
                    print(f"      ⚡ Risk: {agent['risk_tolerance']}")
                    print(f"      🕐 Last Activity: {agent['last_activity']}")
                    print()
            else:
                print("❌ No agents found")
                
        except Exception as e:
            print(f"❌ Error checking agent status: {e}")
    
    async def get_database_summary(self, conn):
        """Get overall database summary"""
        print("\n📊 DATABASE SUMMARY")
        print("=" * 50)
        
        try:
            # Count records in each table
            tables_info = [
                ('trading.trading_accounts', 'Trading Accounts'),
                ('trading.account_transactions', 'Transactions'),
                ('trading.account_holdings', 'Holdings'),
                ('trading.account_portfolio_snapshots', 'Portfolio Snapshots'),
                ('agents.trading_agents', 'Trading Agents')
            ]
            
            for table, description in tables_info:
                try:
                    count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                    print(f"📋 {description}: {count} records")
                except:
                    print(f"❌ {description}: Table not accessible")
            
            # Get latest activity timestamp
            try:
                latest_tx = await conn.fetchval("""
                    SELECT MAX(created_at) FROM trading.account_transactions
                """)
                if latest_tx:
                    print(f"🕐 Latest Transaction: {latest_tx}")
                else:
                    print("🕐 Latest Transaction: None")
            except:
                print("🕐 Latest Transaction: Unable to determine")
                
        except Exception as e:
            print(f"❌ Error getting database summary: {e}")

async def main():
    """Main function to verify PostgreSQL data"""
    verifier = PostgreSQLVerifier()
    
    print("🔍 PHASE 5.2: POSTGRESQL DATA VERIFICATION")
    print("=" * 60)
    print("Checking if agent trading data is being written to PostgreSQL...")
    print("=" * 60)
    
    # Connect to database
    conn = await verifier.connect_to_database()
    if not conn:
        print("❌ Cannot proceed without database connection")
        return
    
    try:
        # Verify database structure
        await verifier.verify_database_structure(conn)
        
        # Check data in each table
        await verifier.check_trading_accounts(conn)
        await verifier.check_transactions(conn)
        await verifier.check_holdings(conn)
        await verifier.check_portfolio_snapshots(conn)
        await verifier.check_agent_status(conn)
        
        # Get summary
        await verifier.get_database_summary(conn)
        
        print("\n✅ PHASE 5.2 COMPLETE!")
        print("🔍 Next: Verify frontend displays this PostgreSQL data")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    asyncio.run(main())