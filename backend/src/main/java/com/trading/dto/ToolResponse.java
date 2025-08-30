package com.trading.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class ToolResponse<T> {
    private boolean success;
    private T data;
    private String error;
    
    public static <T> ToolResponse<T> success(T data) {
        return new ToolResponse<>(true, data, null);
    }
    
    public static <T> ToolResponse<T> error(String message) {
        return new ToolResponse<>(false, null, message);
    }
}