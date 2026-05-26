package com.trading.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * STOMP-over-SockJS WebSocket configuration for broadcasting trade events and
 * portfolio updates to the dashboard.
 *
 * <p>Origins permitted to open a SockJS handshake at {@code /api/ws} are sourced
 * from {@link SecurityProperties#getAllowedOrigins()} — the same typed list that
 * feeds the global {@code CorsFilter} in {@link CorsConfig}. Sharing the source
 * keeps the SockJS handshake check and the REST CORS check from drifting and
 * provides defense-in-depth: if the {@code /api/**} CORS registration is ever
 * loosened or a non-browser client routes around the CORS filter, the SockJS
 * handler still rejects unrecognized origins at the handshake layer.
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    private final SecurityProperties securityProperties;

    public WebSocketConfig(SecurityProperties securityProperties) {
        this.securityProperties = securityProperties;
    }

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
        // Client requests /api/ws -> Traefik forwards as-is -> backend receives /api/ws
        registry.addEndpoint("/api/ws")
                .setAllowedOriginPatterns(securityProperties.getAllowedOrigins().toArray(new String[0]))
                .withSockJS(); // Fallback for browsers without WebSocket support
    }
}
