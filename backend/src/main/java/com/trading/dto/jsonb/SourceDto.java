package com.trading.dto.jsonb;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 * DTO for source attribution in research and decision phases.
 * Per design doc: web sources (verifiable URLs) or system_context (internal tool usage).
 *
 * Implements {@link Serializable} because Hibernate 6.6 (Spring Boot 3.5) requires
 * JSONB-mapped entity attributes to be Serializable for the default JsonSerializer
 * dirty-checking path.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class SourceDto implements Serializable {

    private static final long serialVersionUID = 1L;


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

