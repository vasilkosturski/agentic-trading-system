package com.trading.dto.jsonb;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * DTO for source attribution in research and decision phases.
 * Per design doc: web sources (verifiable URLs) or system_context (internal tool usage).
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SourceDto {
    
    /**
     * Source type: "web" or "system_context"
     */
    private String type;
    
    /**
     * Title for web sources (e.g., "JPMorgan Q4 earnings beat expectations")
     */
    private String title;
    
    /**
     * URL for web sources (clickable, verifiable)
     */
    private String url;
    
    /**
     * Description for system_context sources (e.g., "Checked portfolio: 8 positions")
     */
    private String description;
}

