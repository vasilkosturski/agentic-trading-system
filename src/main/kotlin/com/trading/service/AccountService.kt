package com.trading.service

import com.fasterxml.jackson.databind.ObjectMapper
import com.trading.entity.*
import com.trading.repository.AccountRepository
import com.trading.repository.LogRepository
import org.springframework.beans.factory.annotation.Value
import org.springframework.stereotype.Service
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

@Service
class AccountService(
    private val accountRepository: AccountRepository,
    private val logRepository: LogRepository,
    private val marketService: MarketService,
    private val objectMapper: ObjectMapper,
    @Value("\${trading.initial-balance}") private val initialBalance: Double,
    @Value("\${trading.spread}") private val spread: Double
) {
    
    fun getAccount(name: String): AccountData {
        val account = accountRepository.findByName(name.lowercase())
            ?: createNewAccount(name)
        return account.toAccountData()
    }
    
    private fun createNewAccount(name: String): Account {
        val accountData = AccountData(
            name = name.lowercase(),
            balance = initialBalance,
            strategy = "",
            holdings = emptyMap(),
            transactions = emptyList(),
            portfolioValueTimeSeries = emptyList()
        )
        val account = Account.fromAccountData(name, accountData)
        return accountRepository.save(account)
    }
    
    fun getBalance(name: String): Double {
        return getAccount(name).balance
    }
    
    fun getHoldings(name: String): Map<String, Int> {
        return getAccount(name).holdings
    }
    
    fun buyShares(name: String, symbol: String, quantity: Int, rationale: String): String {
        val accountData = getAccount(name)
        val price = marketService.getSharePrice(symbol)
        val buyPrice