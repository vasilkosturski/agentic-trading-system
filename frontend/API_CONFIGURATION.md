# Frontend API Configuration

## Overview

The frontend uses a **proper environment-based configuration** to handle API endpoints across different environments (development, production).

## How It Works

### Configuration Files

1. **`vite.config.ts`** - Default fallback:
   - Exports `VITE_API_BASE_URL = '/api'`
   - Relative path: frontend uses same origin as where it's served from

2. **`docker-compose.yml`** (Local Development):
   - Sets `VITE_API_BASE_URL: http://localhost:8080/api`
   - Explicit backend URL for when frontend and backend run on different ports
   - Vite dev server proxies `/api` requests to backend at `http://localhost:8080`

3. **`k8s-manifests/03-configmap.yaml`** (Production):
   - Sets `VITE_API_BASE_URL: /api`
   - Relative path: works through Traefik ingress
   - Frontend and backend both served from `https://agentic-trading.vkontech.com`

### Environment-Specific Behavior

| Environment | `VITE_API_BASE_URL` | How It Works |
|---|---|---|
| **Local Dev** | `http://localhost:8080/api` | Explicit URL, Vite dev server proxies requests |
| **Docker Compose** | `http://localhost:8080/api` | Explicit URL, docker-compose networking |
| **Production (K3s)** | `/api` | Relative path, Traefik ingress proxies to backend-service |

### Implementation

The `webSocketService.ts` intelligently handles both absolute and relative URLs:

```typescript
// If URL is absolute (has http/https), use it directly
if (apiUrl.startsWith('http')) {
  wsUrl = apiUrl.replace(/^https?/, 'ws') + '/ws';
}
// If URL is relative (/api), use current window location
else {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  wsUrl = `${protocol}://${window.location.host}${apiUrl}/ws`;
}
```

This allows:
- **Dev**: `http://localhost:8080/api` → `ws://localhost:8080/api/ws`
- **Prod**: `/api` → `wss://agentic-trading.vkontech.com/api/ws`

## No Hardcoded URLs

✅ No localhost hardcoding
✅ No environment variable hacks
✅ Configuration through proper channels:
  - `docker-compose.yml` for local development
  - Kubernetes ConfigMap for production
  - Vite's dev server proxy for local API access

## Adding New Environments

To add a new environment:

1. Add `VITE_API_BASE_URL` to the appropriate config:
   - `docker-compose.yml` for Docker environments
   - K8s ConfigMap for Kubernetes environments

2. The frontend code automatically adapts to the provided URL.

That's it! No code changes needed.


