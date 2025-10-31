# Agentic Trading System - Frontend

Modern React TypeScript frontend for the Agentic Trading System, built with Vite and deployed to Kubernetes.

## Features

- **Modern Stack**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS with custom trading theme
- **Real-time Data**: Auto-refresh every 15 seconds
- **Routing**: React Router for navigation
- **Charts**: Portfolio performance visualization
- **Icons**: Lucide React icons
- **Responsive**: Works on desktop and mobile

## Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Local Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:5173`

### Production Build

```bash
# Build for production
npm run build

# Preview production build
npm run preview
```

## Configuration

### Environment Variables

Create a `.env` file for local development:

```env
VITE_API_BASE_URL=http://localhost:8080/api
VITE_APP_NAME=Agentic Trading System
VITE_APP_VERSION=1.0.0
```

For production (K8s deployment), these are set via ConfigMap.

### Vite Configuration

The [`vite.config.ts`](vite.config.ts) includes:
- **API Proxy**: Development proxy to backend
- **Host Configuration**: Allows external connections (for K8s)
- **Build Optimization**: Production-ready builds

## Project Structure

```
src/
├── components/
│   └── TradingDashboard/     # Main dashboard components
│       ├── TradingDashboard.tsx
│       ├── RecentTrades.tsx
│       └── SimplePortfolioChart.tsx
├── services/                 # API integration layer
│   ├── api.ts               # Base API configuration
│   ├── tradingService.ts    # Trading agents API
│   ├── marketService.ts     # Market data API
│   ├── portfolioService.ts  # Portfolio history API
│   └── tradesService.ts     # Recent trades API
├── hooks/                   # Custom React hooks
│   ├── useTrading.ts        # Trading agents data
│   ├── useMarketData.ts     # Market status
│   ├── usePortfolioHistory.ts # Portfolio charts
│   └── useRecentTrades.ts   # Recent trades
├── App.tsx                  # Main application
├── main.tsx                 # App entry point
└── index.css               # Global Tailwind styles
```

## Trading Dashboard

The dashboard displays:

### Agent Cards (4 Traders)
- **Warren** – Value investor
- **George** – Macro / momentum
- **Ray** – Risk parity
- **Cathie** – Innovation/growth

Each card shows:
- Portfolio value and daily P&L
- Total trades and success rate
- Current positions count
- 7-day portfolio chart
- Last activity timestamp

### Recent Trades Table
- **Real-time data** from all agents
- **Filtering** by agent, symbol, type
- **Search** functionality
- **Pagination** for large datasets
- **Sorting** by any column

### Market Status
- **Live indicator** (Open/Closed)
- **Next event** timing
- **Current time** display

## API Integration

### Endpoints Used
- `GET /api/market/status` - Market status
- `GET /api/trading/agents/status` - Agent data
- `GET /api/accounts/portfolio/{agent}/history` - Charts
- `GET /api/accounts/trades/recent` - Trade history

### Error Handling
- **Graceful degradation** when APIs are unavailable
- **Loading states** for better UX
- **Retry logic** for failed requests
- **User feedback** for errors

## Scripts

- `npm run dev` - Start development server (port 5173)
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run type-check` - TypeScript checking

## Deployment

### Local Development
Run with `npm run dev` and connect to local backend on port 8080.

### Production (K8s)
Deployed automatically via [`../../deploy-to-k3s.sh`](../../deploy-to-k3s.sh) script.

The production build:
- Serves static files via nginx
- Connects to backend via Kubernetes services
- Uses environment variables from ConfigMap
- Includes proper CORS and security headers

## Technology Stack

- **React 18** - UI framework with hooks
- **TypeScript** - Type safety and better DX
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **Axios** - HTTP client for API calls
- **React Router** - Client-side routing
- **Lucide React** - Modern icon library