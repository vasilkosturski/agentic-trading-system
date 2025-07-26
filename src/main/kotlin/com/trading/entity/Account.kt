package com.trading.entity

import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.kotlin.jacksonObjectMapper
import com.fasterxml.jackson.module.kotlin.readValue
import jakarta.persistence.*
import java.time.LocalDateTime

@Entity
@Table(name = "accounts")
data class Account(
    @Id
    val name: String,
    
    @Column(columnDefinition = "TEXT")
    val account: String
) {
    companion object {
        private val objectMapper: ObjectMapper = jacksonObjectMapper()
        
        fun fromAccountData(name: String, accountData: AccountData): Account {
            return Account(
                name = name.lowercase(),
                account = objectMapper.writeValueAsString(accountData)
            )
        }
    }
    
    fun toAccountData(): AccountData {
        return objectMapper.readValue(account)
    }
}

@JsonIgnoreProperties(ignoreUnknown = true)
data class AccountData(
    val name: String,
    val balance: Double,
    val strategy: String,
    val holdings: Map<String, Int>,
    val transactions: List<Transaction>,
    val portfolioValueTimeSeries: List<PortfolioSnapshot>
)

data class Transaction(
    val symbol: String,
    val quantity: Int,
    val price: Double,
    val timestamp: String,
    val rationale: String
) {
    fun total(): Double = quantity * price
    
    override fun toString(): String {
        return "${kotlin.math.abs(quantity)} shares of $symbol at $price each."
    }
}

data class PortfolioSnapshot(
    val timestamp: String,
    val value: Double
)

@Entity
@Table(name = "logs")
data class LogEntry(
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    val id: Long = 0,
    
    val name: String,
    val datetime: LocalDateTime = LocalDateTime.now(),
    val type: String,
    val message: String
)

@Entity
@Table(name = "market")
data class MarketData(
    @Id
    val date: String,
    
    @Column(columnDefinition = "TEXT")
    val data: String
)