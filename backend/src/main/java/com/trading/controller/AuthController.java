package com.trading.controller;

import com.trading.dto.request.LoginRequest;
import com.trading.dto.response.LoginResponse;
import com.trading.security.JwtTokenProvider;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

/**
 * REST controller for authentication operations.
 * Handles login requests and JWT token generation.
 *
 * <p>Endpoints:
 * <ul>
 *   <li>POST /api/auth/login - Authenticate user and return JWT token</li>
 * </ul>
 */
@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final AuthenticationManager authenticationManager;
    private final JwtTokenProvider jwtTokenProvider;

    public AuthController(AuthenticationManager authenticationManager, JwtTokenProvider jwtTokenProvider) {
        this.authenticationManager = authenticationManager;
        this.jwtTokenProvider = jwtTokenProvider;
    }

    /**
     * Authenticate user and generate JWT token.
     * POST /api/auth/login
     *
     * @param loginRequest credentials (username and password)
     * @return LoginResponse with JWT token and username
     */
    @PostMapping("/login")
    public ResponseEntity<LoginResponse> login(@Valid @RequestBody LoginRequest loginRequest) {
        try {
            // Authenticate user
            Authentication authentication = authenticationManager.authenticate(
                    new UsernamePasswordAuthenticationToken(
                            loginRequest.getUsername(),
                            loginRequest.getPassword()
                    )
            );

            // Generate JWT token
            UserDetails userDetails = (UserDetails) authentication.getPrincipal();
            String token = jwtTokenProvider.generateToken(userDetails);

            // Return token and username
            return ResponseEntity.ok(new LoginResponse(token, userDetails.getUsername()));

        } catch (AuthenticationException e) {
            // Return 401 for invalid credentials
            return ResponseEntity.status(401).build();
        }
    }
}
