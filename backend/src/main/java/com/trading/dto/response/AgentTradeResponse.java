package com.trading.dto.response;

/**
 * Response DTO for agent trade information.
 * Extracted from TradingService for better modularity.
 */
public class AgentTradeResponse {
    private String id;
    private String agentName;
    private String accountId;
    private String symbol;
    private String type;
    private String reasoning;
    private String timestamp;
    private String status;
    private String orderId;
    private int quantity;
    private double price;
    private double confidence;

    public AgentTradeResponse(String id, String agentName, String accountId, String symbol,
                              String type, int quantity, double price, String reasoning,
                              double confidence, String timestamp, String status, String orderId) {
        this.id = id;
        this.agentName = agentName;
        this.accountId = accountId;
        this.symbol = symbol;
        this.type = type;
        this.quantity = quantity;
        this.price = price;
        this.reasoning = reasoning;
        this.confidence = confidence;
        this.timestamp = timestamp;
        this.status = status;
        this.orderId = orderId;
    }

    // Getters
    public String getId() { return id; }
    public String getAgentName() { return agentName; }
    public String getAccountId() { return accountId; }
    public String getSymbol() { return symbol; }
    public String getType() { return type; }
    public int getQuantity() { return quantity; }
    public double getPrice() { return price; }
    public String getReasoning() { return reasoning; }
    public double getConfidence() { return confidence; }
    public String getTimestamp() { return timestamp; }
    public String getStatus() { return status; }
    public String getOrderId() { return orderId; }
}

