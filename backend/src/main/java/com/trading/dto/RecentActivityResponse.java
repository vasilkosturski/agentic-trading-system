package com.trading.dto;

import java.util.List;

public class RecentActivityResponse {
    private String agentName;
    private int days;
    private List<Run> runs;
    private int totalRuns;
    private int totalTrades;

    public static class Run {
        private String date;
        private String outcome;
        private String summary;
        private List<Trade> trades;

        public String getDate() { return date; }
        public void setDate(String date) { this.date = date; }
        public String getOutcome() { return outcome; }
        public void setOutcome(String outcome) { this.outcome = outcome; }
        public String getSummary() { return summary; }
        public void setSummary(String summary) { this.summary = summary; }
        public List<Trade> getTrades() { return trades; }
        public void setTrades(List<Trade> trades) { this.trades = trades; }
    }

    public static class Trade {
        private String type;
        private String symbol;
        private int quantity;
        private double price;
        private String rationale;

        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getSymbol() { return symbol; }
        public void setSymbol(String symbol) { this.symbol = symbol; }
        public int getQuantity() { return quantity; }
        public void setQuantity(int quantity) { this.quantity = quantity; }
        public double getPrice() { return price; }
        public void setPrice(double price) { this.price = price; }
        public String getRationale() { return rationale; }
        public void setRationale(String rationale) { this.rationale = rationale; }
    }

    public String getAgentName() { return agentName; }
    public void setAgentName(String agentName) { this.agentName = agentName; }
    public int getDays() { return days; }
    public void setDays(int days) { this.days = days; }
    public List<Run> getRuns() { return runs; }
    public void setRuns(List<Run> runs) { this.runs = runs; }
    public int getTotalRuns() { return totalRuns; }
    public void setTotalRuns(int totalRuns) { this.totalRuns = totalRuns; }
    public int getTotalTrades() { return totalTrades; }
    public void setTotalTrades(int totalTrades) { this.totalTrades = totalTrades; }
}

