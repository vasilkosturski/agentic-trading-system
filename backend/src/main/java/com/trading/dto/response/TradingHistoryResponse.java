package com.trading.dto.response;

import java.util.List;

public class TradingHistoryResponse {
    private String symbol;
    private String agentName;
    private int days;
    private Position currentPosition;
    private List<Trade> trades;
    private Summary summary;

    public static class Position {
        private int shares;
        private double averageCost;

        public Position(int shares, double averageCost) {
            this.shares = shares;
            this.averageCost = averageCost;
        }

        public int getShares() { return shares; }
        public void setShares(int shares) { this.shares = shares; }
        public double getAverageCost() { return averageCost; }
        public void setAverageCost(double averageCost) { this.averageCost = averageCost; }
    }

    public static class Trade {
        private String date;
        private String type;
        private int quantity;
        private double price;
        private double totalAmount;
        private String rationale;
        private String fullReasoning;

        public String getDate() { return date; }
        public void setDate(String date) { this.date = date; }
        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public int getQuantity() { return quantity; }
        public void setQuantity(int quantity) { this.quantity = quantity; }
        public double getPrice() { return price; }
        public void setPrice(double price) { this.price = price; }
        public double getTotalAmount() { return totalAmount; }
        public void setTotalAmount(double totalAmount) { this.totalAmount = totalAmount; }
        public String getRationale() { return rationale; }
        public void setRationale(String rationale) { this.rationale = rationale; }
        public String getFullReasoning() { return fullReasoning; }
        public void setFullReasoning(String fullReasoning) { this.fullReasoning = fullReasoning; }
    }

    public static class Summary {
        private int totalTrades;
        private int buys;
        private int sells;
        private String pattern;

        public int getTotalTrades() { return totalTrades; }
        public void setTotalTrades(int totalTrades) { this.totalTrades = totalTrades; }
        public int getBuys() { return buys; }
        public void setBuys(int buys) { this.buys = buys; }
        public int getSells() { return sells; }
        public void setSells(int sells) { this.sells = sells; }
        public String getPattern() { return pattern; }
        public void setPattern(String pattern) { this.pattern = pattern; }
    }

    public String getSymbol() { return symbol; }
    public void setSymbol(String symbol) { this.symbol = symbol; }
    public String getAgentName() { return agentName; }
    public void setAgentName(String agentName) { this.agentName = agentName; }
    public int getDays() { return days; }
    public void setDays(int days) { this.days = days; }
    public Position getCurrentPosition() { return currentPosition; }
    public void setCurrentPosition(Position currentPosition) { this.currentPosition = currentPosition; }
    public List<Trade> getTrades() { return trades; }
    public void setTrades(List<Trade> trades) { this.trades = trades; }
    public Summary getSummary() { return summary; }
    public void setSummary(Summary summary) { this.summary = summary; }
}

