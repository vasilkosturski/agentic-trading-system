package com.trading.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AgentSummaryDto {
    private Long id;
    private String name;
    private String style;
    private String description; // Fixed: was incorrectly named 'strategy'
    private boolean active;
    private String lastActivity;
    private String systemPrompt; // Full composed system prompt
}
