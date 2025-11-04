package com.trading.controller;

import com.trading.dto.ToolResponse;
import com.trading.model.AgentStatusUpdate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;

/**
 * Receives status updates from Python agents and broadcasts them to WebSocket clients
 */
@RestController
@RequestMapping("/api/agents")
@CrossOrigin(origins = "*")
public class AgentStatusController {
    
    private static final Logger logger = LoggerFactory.getLogger(AgentStatusController.class);
    
    @Autowired
    private SimpMessagingTemplate messagingTemplate;
    
    /**
     * Receive status update from agent and broadcast to all WebSocket subscribers
     */
    @PostMapping("/status")
    public ResponseEntity<ToolResponse<String>> updateStatus(@RequestBody AgentStatusUpdate update) {
        try {
            // Set timestamp if not provided
            if (update.getTimestamp() == null) {
                update.setTimestamp(Instant.now());
            }
            
            logger.info("Agent status update: {} - {} - {} ({}%)", 
                    update.getAgentName(), 
                    update.getPhase(), 
                    update.getMessage(),
                    update.getProgress());
            
            // Broadcast to all WebSocket subscribers on /topic/agent-status
            messagingTemplate.convertAndSend("/topic/agent-status", update);
            
            return ResponseEntity.noContent().build(); // 204 No Content
            
        } catch (Exception e) {
            logger.error("Error broadcasting agent status", e);
            return ResponseEntity.status(500).body(
                ToolResponse.error("Failed to broadcast status: " + e.getMessage())
            );
        }
    }
}

