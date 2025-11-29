package com.trading.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class HoldingDto {
    private String symbol;
    private Integer quantity;
    private Double averagePrice;  // Optional: average purchase price
}

