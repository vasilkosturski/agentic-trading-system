#!/usr/bin/env python3

import asyncio
import subprocess
import sys
import os
import time
from datetime import datetime
import requests

class Phase5Executor:
    """
    Executes Phase 5: Agent Activation and Real Data Verification
    
    Steps:
    1. Activate agents and generate trading data
    2. Verify PostgreSQL contains the trading data
    3. Verify frontend displays the real data
    4. Create monitoring dashboard
    """
    
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.docker_running = False
    
    def print_phase_header(self, step, title, description):
        """Print formatted phase header"""
        print(f"\n{'='*80}")
        print(f"🚀 PHASE 5.{step}: {title}")
        print(f"{'='*80}")
        print(f"📋 {description}")
        print(f"{'='*80}")
    
    def check_docker_status(self):
        """Check if Docker containers are running"""
        print("\n🐳 CHECKING DOCKER STATUS...")
        
        try:
            result = subprocess.run(['docker-compose', 'ps'], 
                                  capture_output=True, text=True, cwd=self.base_dir)
            
            if result.returncode == 0:
                print("✅ Docker Compose is accessible")
                
                # Check if containers are running
                if 'Up' in result.stdout:
                    print("✅ Docker containers are running")
                    self.docker_running = True
                    
                    # Show container status
                    lines = result.stdout.strip().split('\n')
                    for line in lines[1:]:  # Skip header
                        if line.strip():
                            print(f"   📦 {line}")
                else:
                    print("❌ Docker containers are not running")
                    print("🔧 Starting Docker containers...")
                    self.start_docker_containers()
            else:
                print(f"❌ Docker Compose error: {result.stderr}")
                return False
                
        except FileNotFoundError:
            print("❌ Docker Compose not found. Please install Docker.")
            return False
        except Exception as e:
            print(f"❌ Error checking Docker status: {e}")
            return False
        
        return self.docker_running
    
    def start_docker_containers(self):
        """Start Docker containers"""
        try:
            print("🚀 Starting Docker containers...")
            result = subprocess.run(['docker-compose', 'up', '-d', '--build'], 
                                  cwd=self.base_dir, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Docker containers started successfully")
                self.docker_running = True
                
                # Wait for services to be ready
                print("⏳ Waiting for services to be ready...")
                time.sleep(30)
                
            else:
                print(f"❌ Failed to start Docker containers: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error starting Docker containers: {e}")
            return False
        
        return True
    
    def check_backend_health(self):
        """Check if backend is healthy"""
        print("\n🏥 CHECKING BACKEND HEALTH...")
        
        try:
            response = requests.get('http://localhost:8080/actuator/health', timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                print(f"✅ Backend is healthy: {health_data.get('status', 'Unknown')}")
                return True
            else:
                print(f"❌ Backend health check failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot reach backend: {e}")
            return False
    
    def check_frontend_health(self):
        """Check if frontend is accessible"""
        print("\n🖥️  CHECKING FRONTEND HEALTH...")
        
        try:
            response = requests.get('http://localhost:5173', timeout=10)
            if response.status_code == 200:
                print("✅ Frontend is accessible")
                return True
            else:
                print(f"❌ Frontend health check failed: {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Cannot reach frontend: {e}")
            return False
    
    async def run_step1_activate_agents(self):
        """Step 1: Activate agents and generate trading data"""
        self.print_phase_header(1, "AGENT ACTIVATION", 
                               "Activate 4 autonomous trading agents and generate real trading activity")
        
        try:
            # Run agent activation script
            print("🤖 Running agent activation script...")
            
            # Use Python to run the activation script
            process = await asyncio.create_subprocess_exec(
                sys.executable, 'activate_agents.py',
                cwd=self.base_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print("✅ Agent activation completed successfully")
                print("\n📊 AGENT ACTIVATION OUTPUT:")
                print("-" * 50)
                print(stdout.decode())
                return True
            else:
                print(f"❌ Agent activation failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Error running agent activation: {e}")
            return False
    
    async def run_step2_verify_postgres(self):
        """Step 2: Verify PostgreSQL contains trading data"""
        self.print_phase_header(2, "POSTGRESQL VERIFICATION", 
                               "Verify that trading data is being written to PostgreSQL database")
        
        try:
            # Run PostgreSQL verification script
            print("🔍 Running PostgreSQL verification script...")
            
            process = await asyncio.create_subprocess_exec(
                sys.executable, 'verify_postgres_data.py',
                cwd=self.base_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                print("✅ PostgreSQL verification completed")
                print("\n📊 POSTGRESQL VERIFICATION OUTPUT:")
                print("-" * 50)
                print(stdout.decode())
                return True
            else:
                print(f"❌ PostgreSQL verification failed: {stderr.decode()}")
                return False
                
        except Exception as e:
            print(f"❌ Error running PostgreSQL verification: {e}")
            return False
    
    def run_step3_verify_frontend(self):
        """Step 3: Verify frontend displays real data"""
        self.print_phase_header(3, "FRONTEND VERIFICATION", 
                               "Verify that frontend displays real trading data from PostgreSQL")
        
        try:
            # Check if frontend is accessible
            if not self.check_frontend_health():
                return False
            
            # Test API endpoints that frontend uses
            print("\n🔌 TESTING API ENDPOINTS...")
            
            api_endpoints = [
                '/api/accounts',
                '/api/accounts/status',
                '/api/market/status',
                '/api/trading/agents'
            ]
            
            for endpoint in api_endpoints:
                try:
                    url = f'http://localhost:8080{endpoint}'
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"✅ {endpoint}: {len(data.get('data', []))} records")
                    else:
                        print(f"❌ {endpoint}: HTTP {response.status_code}")
                        
                except Exception as e:
                    print(f"❌ {endpoint}: {e}")
            
            print(f"\n🖥️  Frontend is accessible at: http://localhost:5173")
            print("👀 Please manually verify that the dashboard shows:")
            print("   • Real agent portfolio values (not static $100,000)")
            print("   • Actual trade counts (not 0)")
            print("   • Live P&L changes")
            print("   • Recent trading activity")
            
            # Wait for user confirmation
            input("\n⏳ Press Enter after verifying the frontend displays real data...")
            
            return True
            
        except Exception as e:
            print(f"❌ Error verifying frontend: {e}")
            return False
    
    def create_monitoring_script(self):
        """Step 4: Create monitoring script"""
        self.print_phase_header(4, "MONITORING SETUP", 
                               "Create monitoring script to track ongoing agent activity")
        
        monitoring_script = '''#!/usr/bin/env python3

import asyncio
import requests
import time
from datetime import datetime

async def monitor_system():
    """Monitor the trading system continuously"""
    print("🔍 AGENTIC TRADING SYSTEM MONITOR")
    print("=" * 50)
    print("Press Ctrl+C to stop monitoring")
    print("=" * 50)
    
    while True:
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"\\n📊 System Status - {timestamp}")
            print("-" * 40)
            
            # Check backend health
            try:
                response = requests.get('http://localhost:8080/actuator/health', timeout=5)
                if response.status_code == 200:
                    print("✅ Backend: Healthy")
                else:
                    print(f"❌ Backend: HTTP {response.status_code}")
            except:
                print("❌ Backend: Unreachable")
            
            # Check agent status
            try:
                response = requests.get('http://localhost:8080/api/trading/agents', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    agents = data.get('data', [])
                    print(f"🤖 Agents: {len(agents)} active")
                    
                    for agent in agents:
                        name = agent.get('agentName', 'Unknown')
                        portfolio = agent.get('portfolioValue', 0)
                        trades = agent.get('totalTrades', 0)
                        print(f"   👤 {name}: ${portfolio:,.2f}, {trades} trades")
                else:
                    print(f"❌ Agents: HTTP {response.status_code}")
            except:
                print("❌ Agents: API Error")
            
            # Check recent transactions
            try:
                response = requests.get('http://localhost:8080/api/accounts', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    accounts = data.get('data', [])
                    total_trades = sum(acc.get('totalTrades', 0) for acc in accounts)
                    total_value = sum(acc.get('portfolioValue', 0) for acc in accounts)
                    print(f"💰 Total Portfolio: ${total_value:,.2f}")
                    print(f"📈 Total Trades: {total_trades}")
                else:
                    print(f"❌ Accounts: HTTP {response.status_code}")
            except:
                print("❌ Accounts: API Error")
            
            # Wait 30 seconds before next check
            await asyncio.sleep(30)
            
        except KeyboardInterrupt:
            print("\\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Monitor error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(monitor_system())
'''
        
        try:
            monitor_path = os.path.join(self.base_dir, 'monitor_system.py')
            with open(monitor_path, 'w') as f:
                f.write(monitoring_script)
            
            # Make it executable
            os.chmod(monitor_path, 0o755)
            
            print(f"✅ Created monitoring script: {monitor_path}")
            print("🔍 Run with: python monitor_system.py")
            
            return True
            
        except Exception as e:
            print(f"❌ Error creating monitoring script: {e}")
            return False
    
    async def run_complete_phase5(self):
        """Run complete Phase 5 execution"""
        print("🚀 PHASE 5: AGENT ACTIVATION AND REAL DATA VERIFICATION")
        print("=" * 80)
        print("This phase will:")
        print("1. ✅ Activate 4 autonomous trading agents")
        print("2. 🔍 Verify PostgreSQL contains real trading data") 
        print("3. 🖥️  Verify frontend displays live trading activity")
        print("4. 📊 Set up monitoring for ongoing activity")
        print("=" * 80)
        
        # Prerequisites check
        print("\n🔧 CHECKING PREREQUISITES...")
        if not self.check_docker_status():
            print("❌ Docker containers must be running. Please start them first.")
            return False
        
        if not self.check_backend_health():
            print("❌ Backend must be healthy. Please check the backend service.")
            return False
        
        print("✅ All prerequisites met!")
        
        # Execute each step
        steps = [
            ("Step 1", self.run_step1_activate_agents),
            ("Step 2", self.run_step2_verify_postgres),
            ("Step 3", self.run_step3_verify_frontend),
            ("Step 4", self.create_monitoring_script)
        ]
        
        results = []
        
        for step_name, step_func in steps:
            print(f"\n🎯 Executing {step_name}...")
            
            if asyncio.iscoroutinefunction(step_func):
                success = await step_func()
            else:
                success = step_func()
            
            results.append((step_name, success))
            
            if success:
                print(f"✅ {step_name} completed successfully")
            else:
                print(f"❌ {step_name} failed")
                
                # Ask if user wants to continue
                response = input(f"❓ Continue to next step? (y/n): ").lower()
                if response != 'y':
                    break
        
        # Print final summary
        print(f"\n{'='*80}")
        print("📊 PHASE 5 EXECUTION SUMMARY")
        print(f"{'='*80}")
        
        for step_name, success in results:
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{step_name}: {status}")
        
        successful_steps = sum(1 for _, success in results if success)
        total_steps = len(results)
        
        print(f"\n🎯 Overall: {successful_steps}/{total_steps} steps completed successfully")
        
        if successful_steps == total_steps:
            print("\n🎉 PHASE 5 COMPLETE!")
            print("🚀 The agentic trading system is now active with real data!")
            print("🖥️  Frontend: http://localhost:5173")
            print("📊 Monitor: python monitor_system.py")
        else:
            print(f"\n⚠️  Phase 5 partially completed ({successful_steps}/{total_steps})")
            print("🔧 Please address the failed steps before proceeding")
        
        return successful_steps == total_steps

async def main():
    """Main execution function"""
    executor = Phase5Executor()
    
    try:
        success = await executor.run_complete_phase5()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\n⏹️  Phase 5 execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Phase 5 execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())