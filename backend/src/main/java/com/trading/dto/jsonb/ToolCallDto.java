package com.trading.dto.jsonb;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import java.io.Serializable;
import java.util.Map;
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
@JsonIgnoreProperties(ignoreUnknown = true)
@SuppressWarnings("serial") // Map<String, Object> is the interface type Jackson populates from JSONB
public class ToolCallDto implements Serializable {

    private static final long serialVersionUID = 1L;

    private String tool;

    private Map<String, Object> params;

    private Boolean error;

    private String errorMessage;

    public ToolCallDto(String tool) {
        this.tool = tool;
        this.params = null;
        this.error = null;
        this.errorMessage = null;
    }
}
