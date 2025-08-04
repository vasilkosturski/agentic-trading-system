# Agentic Trading System - Frontend

Modern React TypeScript frontend for the Agentic Trading System, built with Vite.

## Features

- **Modern Stack**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS with custom trading theme
- **State Management**: React Query for server state
- **Routing**: React Router for navigation
- **Charts**: Recharts for data visualization
- **Icons**: Lucide React icons

## Quick Start

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Development

The app will be available at `http://localhost:3000`

- **Hot reload**: Changes appear instantly
- **TypeScript**: Full type checking
- **Linting**: ESLint with React rules
- **API Proxy**: Backend calls proxied to `http://localhost:8080`

## Project Structure

```
src/
├── components/           # React components
│   └── TradingDashboard/ # Main dashboard
├── services/            # API integration (next step)
├── hooks/               # Custom React hooks (next step)
├── types/               # TypeScript types (next step)
├── utils/               # Utility functions (next step)
├── App.tsx              # Main app component
├── main.tsx             # App entry point
└── index.css            # Global styles
```

## Backend Integration

The frontend connects to the Java Spring Boot backend:

- **API Base URL**: `http://localhost:8080`
- **Proxy**: Vite dev server proxies `/api/*` requests
- **Authentication**: To be implemented
- **Real-time**: WebSocket integration planned

## Trading Dashboard

Replicates the 4-trader layout from the source project:

- **Warren**: Value investing (Buffett style)
- **George**: Macro trading (Soros style)  
- **Ray**: Systematic approach (Dalio style)
- **Cathie**: Innovation focus (Wood style)

Each trader displays:
- Portfolio value with P&L
- Real-time activity logs
- Holdings and transactions
- Performance charts

## Next Steps

1. **Core UI Components** - Reusable component library
2. **API Integration** - Connect to Java backend
3. **Real-time Updates** - WebSocket integration
4. **Advanced Charts** - Portfolio and market visualization

## Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

## Technology Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **React Query** - Server state management
- **React Router** - Client-side routing
- **Recharts** - Data visualization
- **Lucide React** - Icon library