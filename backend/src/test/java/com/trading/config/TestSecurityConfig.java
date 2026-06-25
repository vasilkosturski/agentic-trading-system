package com.trading.config;

import com.trading.security.JwtAuthenticationFilter;
import com.trading.security.JwtTokenProvider;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.test.context.bean.override.mockito.MockitoBean;

/**
 * Test configuration that provides mock beans for JWT security components.
 * Import this in @WebMvcTest tests that use SecurityConfig.
 */
@TestConfiguration
public class TestSecurityConfig {

    @MockitoBean
    public JwtAuthenticationFilter jwtAuthenticationFilter;

    @MockitoBean
    public JwtTokenProvider jwtTokenProvider;
}
