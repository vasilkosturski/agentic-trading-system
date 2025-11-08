package com.trading.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry config) {
        // Enable simple in-memory message broker to broadcast messages
        config.enableSimpleBroker("/topic");
        // Prefix for messages FROM client to server
        config.setApplicationDestinationPrefixes("/app");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // WebSocket endpoint for clients to connect
        // Register at both /ws and /api/ws to handle Traefik path stripping
        // Client requests /api/ws -> Traefik strips /api -> backend receives /ws
        registry.addEndpoint("/ws", "/api/ws")
                .setAllowedOriginPatterns("*") // Allow all origins for demo
                .withSockJS(); // Fallback for browsers without WebSocket support
    }
}

