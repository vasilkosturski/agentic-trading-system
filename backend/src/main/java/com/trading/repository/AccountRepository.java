package com.trading.repository;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.trading.model.Account;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

import java.sql.*;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Repository
public class AccountRepository {
    
    @Value("${trading.database.path:../agents/accounts.db}")
    private String databasePath;
    
    private final ObjectMapper objectMapper = new ObjectMapper();
    
    private Connection getConnection() throws SQLException {
        return DriverManager.getConnection("jdbc:sqlite:" + databasePath);
    }
    
    public List<Account> findAll() {
        List<Account> accounts = new ArrayList<>();
        String sql = "SELECT name, account FROM accounts";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql);
             ResultSet rs = stmt.executeQuery()) {
            
            while (rs.next()) {
                try {
                    String accountJson = rs.getString("account");
                    Account account = objectMapper.readValue(accountJson, Account.class);
                    accounts.add(account);
                } catch (JsonProcessingException e) {
                    System.err.println("Error parsing account JSON: " + e.getMessage());
                }
            }
        } catch (SQLException e) {
            System.err.println("Database error: " + e.getMessage());
        }
        
        return accounts;
    }
    
    public Optional<Account> findByName(String name) {
        String sql = "SELECT account FROM accounts WHERE name = ?";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, name.toLowerCase());
            ResultSet rs = stmt.executeQuery();
            
            if (rs.next()) {
                String accountJson = rs.getString("account");
                Account account = objectMapper.readValue(accountJson, Account.class);
                return Optional.of(account);
            }
        } catch (SQLException | JsonProcessingException e) {
            System.err.println("Error finding account: " + e.getMessage());
        }
        
        return Optional.empty();
    }
    
    public List<String> getAccountLogs(String name, int limit) {
        List<String> logs = new ArrayList<>();
        String sql = "SELECT datetime, type, message FROM logs WHERE name = ? ORDER BY datetime DESC LIMIT ?";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, name.toLowerCase());
            stmt.setInt(2, limit);
            ResultSet rs = stmt.executeQuery();
            
            while (rs.next()) {
                String logEntry = String.format("[%s] %s: %s", 
                    rs.getString("datetime"),
                    rs.getString("type"),
                    rs.getString("message"));
                logs.add(logEntry);
            }
        } catch (SQLException e) {
            System.err.println("Error getting logs: " + e.getMessage());
        }
        
        return logs;
    }
    
    public void save(Account account) {
        String sql = "INSERT INTO accounts (name, account) VALUES (?, ?) " +
                    "ON CONFLICT(name) DO UPDATE SET account = excluded.account";
        
        try (Connection conn = getConnection();
             PreparedStatement stmt = conn.prepareStatement(sql)) {
            
            stmt.setString(1, account.getName().toLowerCase());
            stmt.setString(2, objectMapper.writeValueAsString(account));
            stmt.executeUpdate();
        } catch (SQLException | JsonProcessingException e) {
            System.err.println("Error saving account: " + e.getMessage());
            throw new RuntimeException("Failed to save account: " + e.getMessage());
        }
    }
}