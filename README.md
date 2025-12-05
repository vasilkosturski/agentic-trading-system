# Agentic Trading System - Local Development Guide

## 🚀 Local Development Setup

This guide covers running the system locally for development purposes. For production deployment, see the main [`DEPLOYMENT.md`](../DEPLOYMENT.md).

### Prerequisites
- Java 17+ (for Spring Boot backend)
- Node.js 18+ (for React frontend)
- PostgreSQL 15+ (or use Docker)

### 1. Database Setup

The schema is generated automatically from the Java entities (`spring.jpa.hibernate.ddl-auto=update`).

#### Option A: Local PostgreSQL

```bash
# Create database + user (run inside psql)
CREATE USER trading_user WITH PASSWORD 'trading_password';
CREATE DATABASE agentic_trading OWNER trading_user;
```

> Tables are created on first backend startup—no SQL scripts required.

#### Option B: Docker PostgreSQL

```bash
docker run --name postgres-dev \
  -e POSTGRES_DB=agentic_trading \
  -e POSTGRES_USER=trading_user \
  -e POSTGRES_PASSWORD=trading_password \
  -p 5432:5432 -d postgres:15
```

### 2. Start the Backend

```bash
cd backend
./gradlew bootRun
```

The backend will start on `http://localhost:8080`

### 3. Start the Frontend

```bash
cd frontend

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
```

The frontend will start on `http://localhost:5173`

### 4. Access the Application

Open your browser to: **http://localhost:5173**

You should see:
- ✅ **4 Trading Agents**: Warren, George, Ray, Cathie
- ✅ **Real-time Data**: Portfolio values, P&L, trading stats
- ✅ **Market Status**: Live market open/closed indicator
- ✅ **Recent Trades**: Sample trading activity
- ✅ **Portfolio Charts**: 7-day performance visualization

## 🔧 Configuration

Note: Docker Compose automatically loads variables from a file named `.env` in this directory. If you use a differently named env file, run Compose with:

```bash
docker compose --env-file .env.custom up -d
```

### Backend Configuration
The backend uses PostgreSQL profile by default. Key configuration in [`src/main/resources/application-postgresql.yml`](backend/src/main/resources/application-postgresql.yml):

```yaml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/agentic_trading
    username: trading_user
    password: trading_password
```

### Frontend Configuration
Create a `.env` file in the `frontend/` directory:

```env
VITE_API_BASE_URL=http://localhost:8080/api
VITE_APP_NAME=Agentic Trading System
VITE_APP_VERSION=1.0.0
```

## 🐛 Troubleshooting

### Backend Issues
- **Port 8080 in use**: Change port in `application.yml`
- **Database connection**: Ensure PostgreSQL is running and accessible
- **Java version**: Verify Java 17+ is installed

### Frontend Issues
- **API connection**: Ensure backend is running on port 8080
- **Dependencies**: Run `npm install` if packages are missing
- **Port conflicts**: Vite will use next available port automatically

### Database Issues
- **Connection refused**: Check PostgreSQL service status
- **Tables missing**: Run the initialization scripts
- **Permission denied**: Verify database user permissions

## 📊 API Endpoints

### Market Data
- `GET /api/market/status` - Current market status and hours

### Trading Agents
- `GET /api/trading/agents/status` - All agents with portfolio data

### Account Management
- `GET /api/accounts/portfolio/{agent}/history?days=7` - Portfolio history
- `GET /api/accounts/trades/recent?limit=50` - Recent trading activity

## 🔄 Development Workflow

1. **Backend Changes**: Restart with `./gradlew bootRun`
2. **Frontend Changes**: Hot reload automatically updates
3. **Database Changes**: Restart backend—JPA migrates schema automatically
4. **API Changes**: Update both backend endpoints and frontend services

## 📁 Component Structure

```
agentic-trading-system/
├── backend/                    # Java Spring Boot backend
│   ├── src/main/java/com/trading/
│   │   ├── controller/        # REST API endpoints
│   │   ├── service/          # Business logic
│   │   ├── entity/           # JPA entities
│   │   └── repository/       # Data access layer
│   └── build.gradle.kts      # Build configuration
├── frontend/                  # React TypeScript frontend
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── hooks/           # Custom React hooks
│   │   ├── services/        # API service layer
│   │   └── App.tsx          # Main application
│   └── package.json         # Dependencies
├── database/                # Database documentation (JPA-managed schema)
└── docs/                    # Technical documentation
```

## 🧪 Testing

### Backend Tests
```bash
cd backend
./gradlew test
```

### Frontend Tests
```bash
cd frontend
npm test
```

### API Testing
```bash
# Test endpoints manually
curl http://localhost:8080/api/market/status
curl http://localhost:8080/api/trading/agents/status
```

## 🎯 Next Steps

1. **View Dashboard**: Access http://localhost:5173
2. **Monitor Agents**: Check trading agent status and activity
3. **Explore APIs**: Test different endpoints
4. **Customize**: Modify agent parameters or add features

For production deployment, use the main deployment script: [`../deploy-to-k3s.sh`](../deploy-to-k3s.sh)test
