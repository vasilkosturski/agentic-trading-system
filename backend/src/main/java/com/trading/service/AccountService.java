package com.trading.service;

import com.trading.entity.Account;
import com.trading.entity.AccountData;
import com.trading.repository.AccountRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;
import java.util.ArrayList;

@Service
public class AccountService {
    
    @Autowired
    private AccountRepository accountRepository;
    
    @Value("${trading.initial-balance}")
    private Double initialBalance;
    
    public AccountData getAccount(String name) {
        Account account = accountRepository.findByName(name.toLowerCase());
        if (account == null) {
            account = createNewAccount(name);
        }
        return account.toAccountData();
    }
    
    private Account createNewAccount(String name) {
        AccountData accountData = new AccountData(
            name.toLowerCase(),
            initialBalance,
            "",
            new HashMap<>(),
            new ArrayList<>(),
            new ArrayList<>()
        );
        Account account = Account.fromAccountData(name, accountData);
        return accountRepository.save(account);
    }
    
    public Double getBalance(String name) {
        return getAccount(name).getBalance();
    }
    
    public Map<String, Integer> getHoldings(String name) {
        return getAccount(name).getHoldings();
    }
    
    public String buyShares(String name, String symbol, Integer quantity, String rationale) {
        // TODO: Implement buy shares logic
        return "Buy shares functionality not yet implemented";
    }
    
    public String sellShares(String name, String symbol, Integer quantity, String rationale) {
        // TODO: Implement sell shares logic
        return "Sell shares functionality not yet implemented";
    }
    
    public String changeStrategy(String name, String strategy) {
        // TODO: Implement change strategy logic
        return "Change strategy functionality not yet implemented";
    }
    
    public String getAccountReport(String name) {
        // TODO: Implement account report logic
        return "Account report functionality not yet implemented";
    }
    
    public String getStrategy(String name) {
        return getAccount(name).getStrategy();
    }
}