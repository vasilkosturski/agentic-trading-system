package com.trading.controller;

import com.trading.config.SecurityConfig;
import com.trading.dto.response.RunListResponseDto;
import com.trading.service.TradingRunService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import java.util.Arrays;
import java.util.Collections;

import static org.hamcrest.Matchers.hasSize;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

/**
 * Security tests for the admin endpoint in TradingRunController.
 * Tests @PreAuthorize("hasRole('ADMIN')") enforcement.
 * Security filters are ENABLED (no @AutoConfigureMockMvc(addFilters = false)).
 */
@WebMvcTest(TradingRunController.class)
@Import(SecurityConfig.class)
@DisplayName("TradingRunController Admin Security Tests")
class TradingRunControllerAdminSecurityTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private TradingRunService tradingRunService;

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("Admin user can access /api/runs/admin and receives 200 OK")
    void listAllRuns_WithAdminRole_Returns200() throws Exception {
        RunListResponseDto response = new RunListResponseDto(
            Collections.emptyList(),
            0L,
            0,
            20
        );
        when(tradingRunService.listRuns(isNull(), any(), eq(true))).thenReturn(response);

        mockMvc.perform(get("/api/runs/admin"))
            .andExpect(status().isOk())
            .andExpect(jsonPath("$.runs", hasSize(0)))
            .andExpect(jsonPath("$.total").value(0));

        // Verify service called with showAll=true
        verify(tradingRunService).listRuns(isNull(), any(), eq(true));
    }

    @Test
    @WithMockUser(roles = "USER")
    @DisplayName("Non-admin user gets 403 Forbidden")
    void listAllRuns_WithoutAdminRole_Returns403() throws Exception {
        mockMvc.perform(get("/api/runs/admin"))
            .andExpect(status().isForbidden());

        // Service should never be called - authorization fails first
        verify(tradingRunService, never()).listRuns(any(), any(), anyBoolean());
    }

    @Test
    @DisplayName("Unauthenticated request gets 401 Unauthorized")
    void listAllRuns_Unauthenticated_Returns401() throws Exception {
        mockMvc.perform(get("/api/runs/admin"))
            .andExpect(status().isUnauthorized());

        // Service should never be called - authentication fails first
        verify(tradingRunService, never()).listRuns(any(), any(), anyBoolean());
    }

    @Test
    @WithMockUser(roles = "ADMIN")
    @DisplayName("Admin endpoint always passes showAll=true to service (no 7-day filter)")
    void listAllRuns_AlwaysPassesShowAllTrue() throws Exception {
        RunListResponseDto response = new RunListResponseDto(
            Collections.emptyList(),
            0L,
            0,
            20
        );
        when(tradingRunService.listRuns(isNull(), any(), eq(true))).thenReturn(response);

        mockMvc.perform(get("/api/runs/admin"))
            .andExpect(status().isOk());

        // Verify showAll=true is always passed (no 7-day filter for admin)
        verify(tradingRunService).listRuns(isNull(), any(), eq(true));
        verify(tradingRunService, never()).listRuns(isNull(), any(), eq(false));
    }
}
