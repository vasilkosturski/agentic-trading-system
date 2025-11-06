import { Client, IMessage } from '@stomp/stompjs';
import SockJS from 'sockjs-client';

export interface AgentStatusUpdate {
  agentId: number;
  agentName: string;
  phase: string;
  message: string;
  progress: number;
  outcome?: string;
  timestamp: string;
}

type StatusCallback = (update: AgentStatusUpdate) => void;

class WebSocketService {
  private client: Client | null = null;
  private callbacks: Set<StatusCallback> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000; // 3 seconds

  connect(apiUrl: string) {
    if (this.client?.connected) {
      console.log('WebSocket already connected');
      return;
    }

    // Convert HTTP/HTTPS URL to WS/WSS
    // apiUrl can be: /api (relative) or http://localhost:8080/api (absolute)
    let wsUrl: string;
    
    if (apiUrl.startsWith('http')) {
      // Absolute URL: convert http/https to ws/wss
      wsUrl = apiUrl.replace(/^https?/, 'ws') + '/ws';
    } else {
      // Relative URL: use window location to determine protocol
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
      const host = window.location.host;
      wsUrl = `${protocol}://${host}${apiUrl}/ws`;
    }
    
    console.log('Connecting to WebSocket:', wsUrl);

    this.client = new Client({
      webSocketFactory: () => new SockJS(wsUrl),
      reconnectDelay: this.reconnectDelay,
      heartbeatIncoming: 10000,
      heartbeatOutgoing: 10000,
      
      onConnect: () => {
        console.log('✅ WebSocket connected');
        this.reconnectAttempts = 0;
        
        // Subscribe to agent status updates
        this.client?.subscribe('/topic/agent-status', (message: IMessage) => {
          try {
            const update: AgentStatusUpdate = JSON.parse(message.body);
            console.log('📡 Agent status update:', update);
            this.callbacks.forEach(callback => callback(update));
          } catch (error) {
            console.error('Failed to parse agent status update:', error);
          }
        });
      },
      
      onDisconnect: () => {
        console.log('❌ WebSocket disconnected');
      },
      
      onStompError: (frame) => {
        console.error('WebSocket error:', frame.headers['message']);
        console.error('Details:', frame.body);
      },
      
      onWebSocketClose: () => {
        console.log('WebSocket connection closed');
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
          this.reconnectAttempts++;
          console.log(`Reconnect attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
        }
      },
    });

    this.client.activate();
  }

  disconnect() {
    if (this.client) {
      console.log('Disconnecting WebSocket...');
      this.client.deactivate();
      this.client = null;
      this.callbacks.clear();
    }
  }

  subscribe(callback: StatusCallback) {
    this.callbacks.add(callback);
    return () => this.callbacks.delete(callback);
  }

  isConnected(): boolean {
    return this.client?.connected || false;
  }
}

// Singleton instance
export const webSocketService = new WebSocketService();

