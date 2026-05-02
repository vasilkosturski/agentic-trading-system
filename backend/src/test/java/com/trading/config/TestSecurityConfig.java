package com.trading.config;

import com.trading.security.JwtAuthenticationFilter;
import com.trading.security.JwtTokenProvider;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.test.mock.mockito.MockBean;

/**
 * Test configuration that provides mock beans for JWT security components.
 * Import this in @WebMvcTest tests that use SecurityConfig.
 */
@TestConfiguration
public class TestSecurityConfig {

    @MockBean
    public JwtAuthenticationFilter jwtAuthenticationFilter;

    @MockBean
    public JwtTokenProvider jwtTokenProvider;
}
