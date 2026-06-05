package com.trading.controller;

import com.trading.model.AgentStatusUpdate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Receives status heartbeats from Python agents. The endpoint is intentionally
 * a no-op apart from logging: the agents pod posts here on every phase
 * transition and expects a 2xx response to confirm the backend is reachable.
 * Payloads are logged at INFO so operators can correlate agent activity with
 * backend logs; nothing is persisted.
 */
@RestController
@RequestMapping("/api/agents")
public class AgentStatusController {

    private static final Logger logger = LoggerFactory.getLogger(AgentStatusController.class);

    /**
     * Acknowledge an agent status heartbeat. Returns 204 No Content on success.
     * Exceptions are handled by GlobalExceptionHandler.
     */
    @PostMapping("/status")
    @PreAuthorize("hasRole('ADMIN')")
    public ResponseEntity<Void> updateStatus(@RequestBody AgentStatusUpdate update) {
        logger.info(
                "Agent status update: {} - {} - {} ({}%)",
                update.getAgentName(), update.getPhase(), update.getMessage(), update.getProgress());

        return ResponseEntity.noContent().build(); // 204 No Content
    }
}
