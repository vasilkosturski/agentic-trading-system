package com.trading.dto.jsonb;

import java.io.Serializable;
import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * Implements {@link Serializable} because Hibernate 6.6 (Spring Boot 3.5) requires
 * JSONB-mapped entity attributes to be Serializable for the default JsonSerializer
 * dirty-checking path.
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ReasoningDto implements Serializable {

    private static final long serialVersionUID = 1L;

    private String rationale;

    private String portfolioContext;

    private String historicalContext;

    private String researchContext;
}
