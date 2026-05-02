package com.trading.security;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.function.Function;

/**
 * JWT token provider for generating and validating JWT tokens.
 * Uses JJWT library with HS256 algorithm.
 *
 * <p>Security considerations:
 * <ul>
 *   <li>Secret key from environment variable (never hardcoded)</li>
 *   <li>Token expiration enforced (configurable, default 1 hour)</li>
 *   <li>HS256 algorithm (HMAC with SHA-256)</li>
 *   <li>Username stored in subject claim</li>
 * </ul>
 */
@Component
public class JwtTokenProvider {

    private final SecretKey secretKey;
    private final long jwtExpirationMs;

    /**
     * Constructor with configurable secret and expiration.
     *
     * <p><strong>IMPORTANT:</strong> jwt.secret MUST be set in application properties or environment variables.
     * There is no default value for security reasons. The secret should be:
     * <ul>
     *   <li>At least 256 bits (32 characters) for HS256</li>
     *   <li>Cryptographically random</li>
     *   <li>Different for each environment (dev, staging, production)</li>
     *   <li>Never committed to version control</li>
     * </ul>
     *
     * @param secret JWT secret key from environment (minimum 256 bits for HS256) - REQUIRED
     * @param jwtExpirationMs Token expiration in milliseconds (default: 1 hour)
     * @throws IllegalArgumentException if secret is null, empty, or too short
     */
    public JwtTokenProvider(
            @Value("${jwt.secret}") String secret,
            @Value("${jwt.expiration:3600000}") long jwtExpirationMs) {
        if (secret == null || secret.trim().isEmpty()) {
            throw new IllegalArgumentException(
                "jwt.secret must be configured in application properties or environment variables. " +
                "It cannot be null or empty for security reasons."
            );
        }
        if (secret.length() < 32) {
            throw new IllegalArgumentException(
                "jwt.secret must be at least 32 characters (256 bits) for HS256 algorithm. " +
                "Current length: " + secret.length()
            );
        }
        this.secretKey = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        this.jwtExpirationMs = jwtExpirationMs;
    }

    /**
     * Generate JWT token for authenticated user.
     *
     * @param userDetails authenticated user details
     * @return JWT token string
     */
    public String generateToken(UserDetails userDetails) {
        Map<String, Object> claims = new HashMap<>();
        return createToken(claims, userDetails.getUsername());
    }

    /**
     * Create JWT token with claims and subject.
     *
     * @param claims additional claims
     * @param subject username
     * @return JWT token string
     */
    private String createToken(Map<String, Object> claims, String subject) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + jwtExpirationMs);

        return Jwts.builder()
                .claims(claims)
                .subject(subject)
                .issuedAt(now)
                .expiration(expiryDate)
                .signWith(secretKey)
                .compact();
    }

    /**
     * Extract username from JWT token.
     *
     * @param token JWT token
     * @return username from token subject
     */
    public String getUsernameFromToken(String token) {
        return extractClaim(token, Claims::getSubject);
    }

    /**
     * Extract expiration date from JWT token.
     *
     * @param token JWT token
     * @return expiration date
     */
    public Date getExpirationDateFromToken(String token) {
        return extractClaim(token, Claims::getExpiration);
    }

    /**
     * Extract a specific claim from JWT token.
     *
     * @param token JWT token
     * @param claimsResolver function to extract claim
     * @param <T> claim type
     * @return extracted claim
     */
    public <T> T extractClaim(String token, Function<Claims, T> claimsResolver) {
        final Claims claims = extractAllClaims(token);
        return claimsResolver.apply(claims);
    }

    /**
     * Extract all claims from JWT token.
     *
     * @param token JWT token
     * @return all claims
     */
    private Claims extractAllClaims(String token) {
        return Jwts.parser()
                .verifyWith(secretKey)
                .build()
                .parseSignedClaims(token)
                .getPayload();
    }

    /**
     * Check if token is expired.
     *
     * @param token JWT token
     * @return true if expired
     */
    private Boolean isTokenExpired(String token) {
        return getExpirationDateFromToken(token).before(new Date());
    }

    /**
     * Validate JWT token against user details.
     *
     * @param token JWT token
     * @param userDetails user details to validate against
     * @return true if valid
     */
    public Boolean validateToken(String token, UserDetails userDetails) {
        try {
            final String username = getUsernameFromToken(token);
            return (username.equals(userDetails.getUsername()) && !isTokenExpired(token));
        } catch (Exception e) {
            return false;
        }
    }
}
