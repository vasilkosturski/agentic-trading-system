package com.trading.security;

import io.jsonwebtoken.ExpiredJwtException;
import io.jsonwebtoken.MalformedJwtException;
import io.jsonwebtoken.security.SignatureException;
import jakarta.servlet.FilterChain;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

/**
 * Unit tests for {@link JwtAuthenticationFilter}.
 *
 * <p>Encodes the contract that the filter must:
 * <ul>
 *   <li>Treat any token failure (missing, expired, malformed, bad signature, unknown user)
 *       as equivalent to an anonymous request.</li>
 *   <li>Always continue the filter chain on token-related failures.</li>
 *   <li>NOT swallow truly unexpected exceptions (e.g., DB outage in UserDetailsService) —
 *       those must propagate so GlobalExceptionHandler can return 500.</li>
 * </ul>
 *
 * <p>See tasks/jwt-auth-fixes/notes/research/03-jwt-filter-symmetry.md.
 */
@ExtendWith(MockitoExtension.class)
@DisplayName("JwtAuthenticationFilter Tests")
class JwtAuthenticationFilterTest {

    @Mock
    private JwtTokenProvider jwtTokenProvider;

    @Mock
    private UserDetailsService userDetailsService;

    @Mock
    private FilterChain filterChain;

    private JwtAuthenticationFilter filter;
    private MockHttpServletRequest request;
    private MockHttpServletResponse response;

    private static final String VALID_TOKEN = "valid.jwt.token";
    private static final String EXPIRED_TOKEN = "expired.jwt.token";
    private static final String MALFORMED_TOKEN = "malformed.jwt.token";
    private static final String BAD_SIG_TOKEN = "bad.signature.token";
    private static final String UNKNOWN_USER_TOKEN = "unknown.user.token";
    private static final String ADMIN_USERNAME = "admin";

    @BeforeEach
    void setUp() {
        filter = new JwtAuthenticationFilter(jwtTokenProvider, userDetailsService);
        request = new MockHttpServletRequest();
        response = new MockHttpServletResponse();
        SecurityContextHolder.clearContext();
    }

    @AfterEach
    void tearDown() {
        SecurityContextHolder.clearContext();
    }

    private UserDetails adminUser() {
        return User.builder()
            .username(ADMIN_USERNAME)
            .password("password")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_ADMIN")))
            .build();
    }

    @Test
    @DisplayName("Missing Authorization header: passes through chain with no authentication")
    void doFilter_NoAuthorizationHeader_ContinuesChainWithoutAuthentication() throws Exception {
        filter.doFilter(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        assertNull(SecurityContextHolder.getContext().getAuthentication(),
            "No Authentication should be set when no Authorization header is present");
        verifyNoInteractions(jwtTokenProvider, userDetailsService);
    }

    @Test
    @DisplayName("Valid Bearer token: sets Authentication on SecurityContext and continues chain")
    void doFilter_ValidToken_SetsAuthenticationAndContinuesChain() throws Exception {
        UserDetails user = adminUser();
        request.addHeader("Authorization", "Bearer " + VALID_TOKEN);
        when(jwtTokenProvider.getUsernameFromToken(VALID_TOKEN)).thenReturn(ADMIN_USERNAME);
        when(userDetailsService.loadUserByUsername(ADMIN_USERNAME)).thenReturn(user);
        when(jwtTokenProvider.validateToken(VALID_TOKEN, user)).thenReturn(true);

        filter.doFilter(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        assertNotNull(auth, "Authentication should be set for a valid token");
        assertEquals(ADMIN_USERNAME, ((UserDetails) auth.getPrincipal()).getUsername());
    }

    @Test
    @DisplayName("Expired Bearer token: swallows ExpiredJwtException, continues chain, no authentication")
    void doFilter_ExpiredToken_SwallowsExceptionAndContinuesChain() throws Exception {
        request.addHeader("Authorization", "Bearer " + EXPIRED_TOKEN);
        when(jwtTokenProvider.getUsernameFromToken(EXPIRED_TOKEN))
            .thenThrow(new ExpiredJwtException(null, null, "JWT expired"));

        filter.doFilter(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        assertNull(SecurityContextHolder.getContext().getAuthentication(),
            "Expired token must not produce an Authentication (treat as anonymous)");
        verify(userDetailsService, never()).loadUserByUsername(anyString());
    }

    @Test
    @DisplayName("Malformed Bearer token: swallows MalformedJwtException, continues chain, no authentication")
    void doFilter_MalformedToken_SwallowsExceptionAndContinuesChain() throws Exception {
        request.addHeader("Authorization", "Bearer " + MALFORMED_TOKEN);
        when(jwtTokenProvider.getUsernameFromToken(MALFORMED_TOKEN))
            .thenThrow(new MalformedJwtException("Malformed JWT"));

        filter.doFilter(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        assertNull(SecurityContextHolder.getContext().getAuthentication(),
            "Malformed token must not produce an Authentication");
        verify(userDetailsService, never()).loadUserByUsername(anyString());
    }

    @Test
    @DisplayName("Bad signature: swallows SignatureException, continues chain, no authentication")
    void doFilter_BadSignatureToken_SwallowsExceptionAndContinuesChain() throws Exception {
        request.addHeader("Authorization", "Bearer " + BAD_SIG_TOKEN);
        when(jwtTokenProvider.getUsernameFromToken(BAD_SIG_TOKEN))
            .thenThrow(new SignatureException("Invalid signature"));

        filter.doFilter(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        assertNull(SecurityContextHolder.getContext().getAuthentication(),
            "Bad-signature token must not produce an Authentication");
        verify(userDetailsService, never()).loadUserByUsername(anyString());
    }

    @Test
    @DisplayName("Unknown username (UserDetailsService throws UsernameNotFoundException): no authentication, chain continues")
    void doFilter_UsernameNotFound_SwallowsExceptionAndContinuesChain() throws Exception {
        request.addHeader("Authorization", "Bearer " + UNKNOWN_USER_TOKEN);
        when(jwtTokenProvider.getUsernameFromToken(UNKNOWN_USER_TOKEN)).thenReturn("ghost");
        when(userDetailsService.loadUserByUsername("ghost"))
            .thenThrow(new UsernameNotFoundException("ghost not found"));

        filter.doFilter(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        assertNull(SecurityContextHolder.getContext().getAuthentication(),
            "Unknown username must not produce an Authentication");
    }

    @Test
    @DisplayName("Valid token but Authentication already in SecurityContext: does not overwrite (idempotency)")
    void doFilter_AuthenticationAlreadySet_DoesNotOverwrite() throws Exception {
        // Pre-populate the SecurityContext with an existing Authentication
        UserDetails preExisting = User.builder()
            .username("preexisting")
            .password("pw")
            .authorities(Collections.singletonList(new SimpleGrantedAuthority("ROLE_USER")))
            .build();
        UsernamePasswordAuthenticationToken preAuth =
            new UsernamePasswordAuthenticationToken(preExisting, null, preExisting.getAuthorities());
        SecurityContextHolder.getContext().setAuthentication(preAuth);

        // The filter receives a valid token. Per the idempotency contract the filter
        // should short-circuit and NOT invoke the token provider or user details service
        // when an Authentication is already present, so we deliberately do not stub them
        // (avoids UnnecessaryStubbingException and asserts the no-interaction contract).
        request.addHeader("Authorization", "Bearer " + VALID_TOKEN);

        filter.doFilter(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        // Pre-existing Authentication must be preserved (idempotency for this filter)
        Authentication current = SecurityContextHolder.getContext().getAuthentication();
        assertNotNull(current);
        assertEquals("preexisting", ((UserDetails) current.getPrincipal()).getUsername(),
            "Filter must not overwrite an existing Authentication");
        // Filter must skip JWT processing entirely when Authentication is already set
        verifyNoInteractions(jwtTokenProvider, userDetailsService);
    }

    @Test
    @DisplayName("Token has null subject: no authentication, chain continues (treated as malformed)")
    void doFilter_NullSubjectInToken_DoesNotSetAuthentication() throws Exception {
        // Simulate JjwtTokenProvider returning a null username — treat as invalid-token equivalent.
        // This is a defensive guard: even if parsing somehow yields a null subject, the filter
        // must NOT pass null into UserDetailsService.loadUserByUsername (which would throw NPE
        // or return spurious results).
        request.addHeader("Authorization", "Bearer " + VALID_TOKEN);
        when(jwtTokenProvider.getUsernameFromToken(VALID_TOKEN)).thenReturn(null);

        filter.doFilter(request, response, filterChain);

        verify(filterChain).doFilter(request, response);
        assertNull(SecurityContextHolder.getContext().getAuthentication(),
            "Null subject must not produce an Authentication");
        verify(userDetailsService, never()).loadUserByUsername(eq(null));
    }

    @Test
    @DisplayName("Unexpected RuntimeException from UserDetailsService PROPAGATES (not swallowed)")
    void doFilter_UnexpectedException_PropagatesAndDoesNotSwallow() throws Exception {
        // Simulate a DB outage or other infrastructure failure inside UserDetailsService.
        // The filter MUST NOT swallow this — it should propagate so the global handler
        // returns a proper 500 instead of silently producing an anonymous request.
        request.addHeader("Authorization", "Bearer " + VALID_TOKEN);
        when(jwtTokenProvider.getUsernameFromToken(VALID_TOKEN)).thenReturn(ADMIN_USERNAME);
        when(userDetailsService.loadUserByUsername(ADMIN_USERNAME))
            .thenThrow(new RuntimeException("Database connection lost"));

        RuntimeException thrown = assertThrows(RuntimeException.class,
            () -> filter.doFilter(request, response, filterChain),
            "Unexpected RuntimeException must propagate, not be swallowed");
        assertEquals("Database connection lost", thrown.getMessage());

        verify(filterChain, never()).doFilter(request, response);
        assertNull(SecurityContextHolder.getContext().getAuthentication());
    }
}
