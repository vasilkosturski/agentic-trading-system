package com.trading.dto.response;

/**
 * Response from the agents service /api/trigger-cycle endpoint.
 * 
 * Success (202): {"message": "Trading cycle triggered successfully.", "status": "TRIGGERED"}
 * Conflict (409): {"message": "A trading cycle is already in progress...", "status": "ALREADY_RUNNING"}
 */
public record TriggerCycleResponse(
    String message,
    String status
) {
    public static TriggerCycleResponse triggered() {
        return new TriggerCycleResponse("Trading cycle triggered successfully.", "TRIGGERED");
    }
    
    public static TriggerCycleResponse alreadyRunning(String message) {
        return new TriggerCycleResponse(
            message != null ? message : "A trading cycle is already in progress.",
            "ALREADY_RUNNING"
        );
    }
}


