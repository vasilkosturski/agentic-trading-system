package com.trading.dto.response;

import lombok.AllArgsConstructor;
import lombok.Data;

/**
 * Response DTO for successful login.
 * Contains JWT token and username.
 */
@Data
@AllArgsConstructor
public class LoginResponse {

    private String token;
    private String username;
}
