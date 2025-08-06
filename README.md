# Agentic Trading System - Quick Start Guide

## 🚀 Running the Full System (Backend + Frontend)

### Prerequisites
- Java 17+ (for Spring Boot backend)
- Node.js 18+ (for React frontend)
- Gradle (included via gradlew)

### 1. Start the Java Spring Boot Backend

```bash
# Navigate to the backend directory
cd agentic-trading-system/backend

# Start the backend (this will run on port 8080)
./gradlew bootRun
```

The backend will be available at: `http://localhost:8080`

### 2. Start the React Frontend

```bash
# Open a new terminal and navigate to frontend
cd agentic-trading-system/frontend

# Install dependencies (if not already done)
npm install

# Start the frontend development server
npm run dev
```

The frontend will be available at: `http://localhost:3000`

### 3. Access the Trading Dashboard

Open your browser and go to: **http://localhost:3000**

You should see:
- ✅ **4 Trading Agents**: Warren, George, Ray, Cathie
- ✅ **Real-time Data**: Portfolio values, P&L, trading stats
- ✅ **Market Status**: Live market open/closed indicator
- ✅ **Auto-refresh**: Data updates every 15 seconds

## 🔧 Configuration

### Backend Configuration
The backend runs on port 8080 by default. Key endpoints:
- `/api/trading/agents/status` - Get all agent statuses
- `/api/accounts` - Account management
- `/api/market/status` - Market status

### Frontend Configuration
Create a `.env` file in the `frontend/` directory:

```env
VITE_API_BASE_URL=http://localhost:8080/api
VITE_APP_NAME=Agentic Trading System
VITE_APP_VERSION=1.0.0
```

## 🐛 Troubleshooting

### Backend Issues
- **Port 8080 in use**: Change port in `application.properties`
- **Java version**: Ensure Java 17+ is installed
- **Database**: H2 database runs in-memory by default

### Frontend Issues
- **Connection Error**: Ensure backend is running on port 8080
- **Port 3000 in use**: Vite will automatically use next available port
- **Dependencies**: Run `npm install` if packages are missing

### Common Issues
1. **CORS Errors**: Backend should have CORS configured for localhost:3000
2. **API 404 Errors**: Check if backend endpoints match frontend service calls
3. **Loading Forever**: Check browser console for network errors

## 📊 What You'll See

### With Backend Running
- Real agent data from the Java APIs
- Live portfolio values and P&L
- Trading statistics and success rates
- Market status indicator

### Without Backend (Frontend Only)
- Professional error handling
- "Connection Error" message
- Graceful degradation of features

## 🔄 Development Workflow

1. **Backend Changes**: Restart `mvn spring-boot:run`
2. **Frontend Changes**: Hot reload automatically updates
3. **API Changes**: Update both backend endpoints and frontend services

## 📁 Project Structure

```
agentic-trading-system/
├── backend/                 # Java Spring Boot backend
├── frontend/               # React TypeScript frontend
├── agents/                 # Python trading agents
├── mcp-servers/           # MCP server implementations
└── docs/                  # Documentation
```

## 🎯 Next Steps

Once both services are running, you can:
1. View the 4 autonomous trading agents
2. Monitor real-time portfolio performance
3. See live market data integration
4. Test the API integration layer

The system is designed to work with or without the Python agents running - the Java backend provides the core trading infrastructure and APIs.