package com.trading.controller;

import com.trading.config.AgentsClient;
import com.trading.dto.response.TriggerCycleResponse;
import com.trading.service.AgentIdentityService;
import com.trading.service.AgentMonitoringService;
import com.trading.service.TradingService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.mockito.Mockito;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.http.HttpStatus;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

/**
 * Tests for TradingController.triggerManualCycle() endpoint.
 *
 * Tests the modern RestClient + Virtual Threads implementation.
 * Uses type-safe @AgentsClient qualifier for mocking.
 *
 * Key test scenarios:
 * - Success path (202 Accepted)
 * - Conflict handling (409 when cycle already running)
 * - Connection error handling (503 when agents service unavailable)
 */
@WebMvcTest(controllers = TradingController.class)
@DisplayName("TradingController.triggerManualCycle() Tests")
class TradingControllerTriggerCycleTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private TradingService tradingService;

    @MockBean
    private AgentMonitoringService agentMonitoringService;

    @MockBean
    private AgentIdentityService agentIdentityService;

    /**
     * Mock RestClient bean with type-safe @AgentsClient qualifier.
     *
     * RestClient uses a fluent API, so we need to mock the chain:
     * restClient.post() → RequestBodyUriSpec → retrieve() → body()
     */
    @MockBean
    @AgentsClient
    private RestClient agentsRestClient;

    @Test
    @DisplayName("Should return 202 Accepted when cycle triggered successfully")
    void triggerManualCycle_Success() throws Exception {
        // Arrange: Mock RestClient fluent API chain
        RestClient.RequestBodyUriSpec requestBodyUriSpec = Mockito.mock(RestClient.RequestBodyUriSpec.class);
        RestClient.ResponseSpec responseSpec = Mockito.mock(RestClient.ResponseSpec.class);

        TriggerCycleResponse expectedResponse = TriggerCycleResponse.triggered();

        when(agentsRestClient.post()).thenReturn(requestBodyUriSpec);
        when(requestBodyUriSpec.uri(anyString())).thenReturn(requestBodyUriSpec);
        when(requestBodyUriSpec.retrieve()).thenReturn(responseSpec);
        when(responseSpec.body(TriggerCycleResponse.class)).thenReturn(expectedResponse);

        // Act & Assert
        mockMvc.perform(post("/api/trading/run-cycle"))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.message").value("Trading cycle triggered successfully."))
                .andExpect(jsonPath("$.status").value("TRIGGERED"));
    }

    @Test
    @DisplayName("Should return 409 Conflict when cycle already running")
    void triggerManualCycle_Conflict() throws Exception {
        // Arrange: Mock RestClient to throw Conflict exception
        RestClient.RequestBodyUriSpec requestBodyUriSpec = Mockito.mock(RestClient.RequestBodyUriSpec.class);
        RestClient.ResponseSpec responseSpec = Mockito.mock(RestClient.ResponseSpec.class);

        when(agentsRestClient.post()).thenReturn(requestBodyUriSpec);
        when(requestBodyUriSpec.uri(anyString())).thenReturn(requestBodyUriSpec);
        when(requestBodyUriSpec.retrieve()).thenReturn(responseSpec);
        when(responseSpec.body(TriggerCycleResponse.class))
                .thenThrow(HttpClientErrorException.Conflict.create(
                        HttpStatus.CONFLICT,
                        "Conflict",
                        null,
                        null,
                        null
                ));

        // Act & Assert: Expect ProblemDetail response
        mockMvc.perform(post("/api/trading/run-cycle"))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.status").value(409))
                .andExpect(jsonPath("$.detail").value("A trading cycle is already in progress. Please wait for it to complete."));
    }

    @Test
    @DisplayName("Should return 503 Service Unavailable when agents service unreachable")
    void triggerManualCycle_ConnectionError() throws Exception {
        // Arrange: Mock RestClient to throw connection exception
        RestClient.RequestBodyUriSpec requestBodyUriSpec = Mockito.mock(RestClient.RequestBodyUriSpec.class);

        when(agentsRestClient.post()).thenReturn(requestBodyUriSpec);
        when(requestBodyUriSpec.uri(anyString())).thenReturn(requestBodyUriSpec);
        when(requestBodyUriSpec.retrieve())
                .thenThrow(new org.springframework.web.client.RestClientException("Connection refused"));

        // Act & Assert: Expect ProblemDetail response
        mockMvc.perform(post("/api/trading/run-cycle"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.status").value(503))
                .andExpect(jsonPath("$.detail").value("Agents service unavailable. Please ensure the trading system is running."));
    }

}
