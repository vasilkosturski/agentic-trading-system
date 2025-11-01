package com.trading.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class AgentSummaryDto {
    private Long id;
    private String name;
    private String strategy;
    private boolean active;
    private String lastActivity;
}

