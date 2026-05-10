package com.trading.security;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests for JwtTokenProvider - token generation and validation.
 * Tests JWT creation, expiration, claims extraction, and validation.
 */
@DisplayName("JwtTokenProvider Tests")
class JwtTokenProviderTest {

    private JwtTokenProvider jwtTokenProvider;
    private static final String TEST_SECRET = "testSecretKeyThatIsLongEnoughForHS256AlgorithmToWorkProperly";
    private static final long TEST_EXPIRATION = 3600000; // 1 hour

    @BeforeEach
    void setUp() {
        jwtTokenProvider = new JwtTokenProvider(TEST_SECRET, TEST_EXPIRATION);
    }

    @Test
    @DisplayName("Generate token with username and role")
    void generateToken_WithUsernameAndRole_ReturnsValidToken() {
        // Arrange
        UserDetails userDetails = User.builder()
            .username("admin")
            .password("password")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_ADMIN")))
            .build();

        // Act
        String token = jwtTokenProvider.generateToken(userDetails);

        // Assert
        assertNotNull(token);
        assertFalse(token.isEmpty());
        assertTrue(token.split("\\.").length == 3); // JWT has 3 parts
    }

    @Test
    @DisplayName("Extract username from valid token")
    void getUsernameFromToken_WithValidToken_ReturnsUsername() {
        // Arrange
        UserDetails userDetails = User.builder()
            .username("admin")
            .password("password")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_ADMIN")))
            .build();
        String token = jwtTokenProvider.generateToken(userDetails);

        // Act
        String username = jwtTokenProvider.getUsernameFromToken(token);

        // Assert
        assertEquals("admin", username);
    }

    @Test
    @DisplayName("Validate token returns true for valid token")
    void validateToken_WithValidToken_ReturnsTrue() {
        // Arrange
        UserDetails userDetails = User.builder()
            .username("admin")
            .password("password")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_ADMIN")))
            .build();
        String token = jwtTokenProvider.generateToken(userDetails);

        // Act
        boolean isValid = jwtTokenProvider.validateToken(token, userDetails);

        // Assert
        assertTrue(isValid);
    }

    @Test
    @DisplayName("Validate token returns false for different username")
    void validateToken_WithDifferentUsername_ReturnsFalse() {
        // Arrange
        UserDetails userDetails1 = User.builder()
            .username("admin")
            .password("password")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_ADMIN")))
            .build();

        UserDetails userDetails2 = User.builder()
            .username("other")
            .password("password")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_ADMIN")))
            .build();

        String token = jwtTokenProvider.generateToken(userDetails1);

        // Act
        boolean isValid = jwtTokenProvider.validateToken(token, userDetails2);

        // Assert
        assertFalse(isValid);
    }

    @Test
    @DisplayName("Validate token returns false for invalid token")
    void validateToken_WithInvalidToken_ReturnsFalse() {
        // Arrange
        UserDetails userDetails = User.builder()
            .username("admin")
            .password("password")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_ADMIN")))
            .build();
        String invalidToken = "invalid.jwt.token";

        // Act
        boolean isValid = jwtTokenProvider.validateToken(invalidToken, userDetails);

        // Assert
        assertFalse(isValid);
    }

    @Test
    @DisplayName("Extract username from invalid token throws exception")
    void getUsernameFromToken_WithInvalidToken_ThrowsException() {
        // Arrange
        String invalidToken = "invalid.jwt.token";

        // Act & Assert
        assertThrows(Exception.class, () -> {
            jwtTokenProvider.getUsernameFromToken(invalidToken);
        });
    }

    @Test
    @DisplayName("Constructor throws exception when secret is null")
    void constructor_WithNullSecret_ThrowsException() {
        // Act & Assert
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            new JwtTokenProvider(null, TEST_EXPIRATION);
        });

        assertTrue(exception.getMessage().contains("jwt.secret must be configured"));
    }

    @Test
    @DisplayName("Constructor throws exception when secret is empty")
    void constructor_WithEmptySecret_ThrowsException() {
        // Act & Assert
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            new JwtTokenProvider("", TEST_EXPIRATION);
        });

        assertTrue(exception.getMessage().contains("jwt.secret must be configured"));
    }

    @Test
    @DisplayName("Constructor throws exception when secret is too short")
    void constructor_WithShortSecret_ThrowsException() {
        // Act & Assert
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class, () -> {
            new JwtTokenProvider("tooshort", TEST_EXPIRATION);
        });

        assertTrue(exception.getMessage().contains("must be at least 32 characters"));
    }

    @Test
    @DisplayName("Constructor accepts secret exactly 32 characters long")
    void constructor_With32CharSecret_Succeeds() {
        // Act & Assert - should not throw
        assertDoesNotThrow(() -> {
            new JwtTokenProvider("12345678901234567890123456789012", TEST_EXPIRATION);
        });
    }

    @Test
    @DisplayName("Validate token returns false for expired token")
    void validateToken_WithExpiredToken_ReturnsFalse() {
        // Arrange: build a provider configured to issue immediately-expired tokens
        // (negative expiration => exp claim is in the past at issue time).
        JwtTokenProvider expiredProvider = new JwtTokenProvider(TEST_SECRET, -1000L);
        UserDetails userDetails = User.builder()
            .username("admin")
            .password("password")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_ADMIN")))
            .build();
        String expiredToken = expiredProvider.generateToken(userDetails);

        // Act: validate via the standard provider (same secret, normal expiration)
        boolean isValid = jwtTokenProvider.validateToken(expiredToken, userDetails);

        // Assert: validateToken must swallow ExpiredJwtException and return false.
        assertFalse(isValid);
    }

    @Test
    @DisplayName("Extract username from expired token throws ExpiredJwtException")
    void getUsernameFromToken_WithExpiredToken_ThrowsExpiredJwtException() {
        // Arrange: an immediately-expired token signed with the same secret.
        JwtTokenProvider expiredProvider = new JwtTokenProvider(TEST_SECRET, -1000L);
        UserDetails userDetails = User.builder()
            .username("admin")
            .password("password")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_ADMIN")))
            .build();
        String expiredToken = expiredProvider.generateToken(userDetails);

        // Act & Assert: getUsernameFromToken must surface the typed JJWT exception so
        // JwtAuthenticationFilter can apply its targeted catch (ExpiredJwtException).
        assertThrows(io.jsonwebtoken.ExpiredJwtException.class,
            () -> jwtTokenProvider.getUsernameFromToken(expiredToken));
    }
}
