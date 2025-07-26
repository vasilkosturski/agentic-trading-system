package com.trading.entity;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.persistence.*;

@Entity
@Table(name = "accounts")
public class Account {
    
    @Id
    private String name;
    
    @Column(columnDefinition = "TEXT")
    private String account;
    
    private static final ObjectMapper objectMapper = new ObjectMapper();
    
    // Constructors
    public Account() {}
    
    public Account(String name, String account) {
        this.name = name;
        this.account = account;
    }
    
    // Static factory method
    public static Account fromAccountData(String name, AccountData accountData) {
        try {
            return new Account(
                name.toLowerCase(),
                objectMapper.writeValueAsString(accountData)
            );
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to serialize account data", e);
        }
    }
    
    // Convert to AccountData
    public AccountData toAccountData() {
        try {
            return objectMapper.readValue(account, AccountData.class);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Failed to deserialize account data", e);
        }
    }
    
    // Getters and Setters
    public String getName() {
        return name;
    }
    
    public void setName(String name) {
        this.name = name;
    }
    
    public String getAccount() {
        return account;
    }
    
    public void setAccount(String account) {
        this.account = account;
    }
}