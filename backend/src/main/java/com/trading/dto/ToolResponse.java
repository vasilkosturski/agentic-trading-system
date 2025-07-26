package com.trading.dto;

public class ToolResponse<T> {
    private boolean success;
    private T data;
    private String error;
    
    public ToolResponse() {}
    
    public ToolResponse(boolean success, T data, String error) {
        this.success = success;
        this.data = data;
        this.error = error;
    }
    
    public static <T> ToolResponse<T> success(T data) {
        return new ToolResponse<>(true, data, null);
    }
    
    public static <T> ToolResponse<T> error(String message) {
        return new ToolResponse<>(false, null, message);
    }
    
    public boolean isSuccess() { return success; }
    public void setSuccess(boolean success) { this.success = success; }
    
    public T getData() { return data; }
    public void setData(T data) { this.data = data; }
    
    public String getError() { return error; }
    public void setError(String error) { this.error = error; }
}