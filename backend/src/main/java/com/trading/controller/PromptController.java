package com.trading.controller;

import com.trading.service.PromptLoader;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.IOException;

/**
 * REST API for serving composed agent prompts.
 * Python agents call this endpoint instead of reading local prompt files.
 */
@RestController
@RequestMapping("/api/prompts")
public class PromptController {

    private final PromptLoader promptLoader;

    public PromptController(PromptLoader promptLoader) {
        this.promptLoader = promptLoader;
    }

    /**
     * Get composed prompt for an agent.
     *
     * @param agentType Agent type (e.g., "decision_maker", "market_analyst")
     * @param agentName Agent name (e.g., "warren", "george", "ray", "cathie")
     * @return Composed prompt with personality substituted
     */
    @GetMapping("/{agentType}/{agentName}")
    public ResponseEntity<String> getPrompt(
            @PathVariable String agentType,
            @PathVariable String agentName) {
        try {
            String prompt = promptLoader.composePrompt(agentType, agentName);
            return ResponseEntity.ok(prompt);
        } catch (IllegalArgumentException e) {
            return ResponseEntity.badRequest().build();
        } catch (IOException e) {
            return ResponseEntity.notFound().build();
        }
    }
}
