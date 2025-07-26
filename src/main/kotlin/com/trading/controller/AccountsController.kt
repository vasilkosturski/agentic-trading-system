package com.trading.controller

import com.trading.service.AccountService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/mcp/accounts")
class AccountsController(
    private val accountService: AccountService
) {
    
    @PostMapping("/tools/get_balance")
    fun getBalance(@RequestBody request: GetBalanceRequest): ResponseEntity<ToolResponse<Double>> {
        return try {
            val balance = accountService.getBalance(request.name)
            ResponseEntity.ok(ToolResponse.success(balance))
        } catch (e: Exception) {
            ResponseEntity.badRequest().body(ToolResponse.error(e.message ?: "Unknown error"))
        }
    }
    
    @PostMapping("/tools/get_holdings")
    fun getHoldings(@RequestBody request: GetHoldingsRequest): ResponseEntity<ToolResponse<Map<String, Int>>> {
        return try {
            val holdings = accountService.getHoldings(request.name)
            ResponseEntity.ok(ToolResponse.success(holdings))
        } catch (e: Exception) {
            ResponseEntity.badRequest().body(ToolResponse.error(e.message ?: "Unknown error"))
        }
    }
    
    @PostMapping("/tools/buy_shares")
    fun buyShares(@RequestBody request: BuySharesRequest): ResponseEntity<ToolResponse<String>> {
        return try {
            val result = accountService.buyShares(request.name, request.symbol, request.quantity, request.rationale)
            ResponseEntity.ok(ToolResponse.success(result))
        } catch (e: Exception) {
            ResponseEntity.badRequest().body(ToolResponse.error(e.message ?: "Unknown error"))
        }
    }
    
    @PostMapping("/tools/sell_shares")
    fun sellShares(@RequestBody request: SellSharesRequest): ResponseEntity<ToolResponse<String>> {
        return try {
            val result = accountService.sellShares(request.name, request.symbol, request.quantity, request.rationale)
            ResponseEntity.ok(ToolResponse.success(result))
        } catch (e: Exception) {
            ResponseEntity.badRequest().body(ToolResponse.error(e.message ?: "Unknown error"))
        }
    }
    
    @PostMapping("/tools/change_strategy")
    fun changeStrategy(@RequestBody request: ChangeStrategyRequest): ResponseEntity<ToolResponse<String>> {
        return try {
            val result = accountService.changeStrategy(request.name, request.strategy)
            ResponseEntity.ok(ToolResponse.success(result))
        } catch (e: Exception) {
            ResponseEntity.badRequest().body(ToolResponse.error(e.message ?: "Unknown error"))
        }
    }
    
    @GetMapping("/resources/accounts/{name}")
    fun getAccountResource(@PathVariable name: String): ResponseEntity<String> {
        return try {
            val report = accountService.getAccountReport(name)
            ResponseEntity.ok(report)
        } catch (e: Exception) {
            ResponseEntity.badRequest().body("Error: ${e.message}")
        }
    }
    
    @GetMapping("/resources/strategy/{name}")
    fun getStrategyResource(@PathVariable name: String): ResponseEntity<String> {
        return try {
            val strategy = accountService.getStrategy(name)
            ResponseEntity.ok(strategy)
        } catch (e: Exception) {
            ResponseEntity.badRequest().body("Error: ${e.message}")
        }
    }
}

// Request DTOs
data class GetBalanceRequest(val name: String)
data class GetHoldingsRequest(val name: String)
data class BuySharesRequest(val name: String, val symbol: String, val quantity: Int, val rationale: String)
data class SellSharesRequest(val name: String, val symbol: String, val quantity: Int, val rationale: String)
data class ChangeStrategyRequest(val name: String, val strategy: String)

// Response wrapper for MCP tools
data class ToolResponse<T>(
    val success: Boolean,
    val data: T? = null,
    val error: String? = null
) {
    companion object {
        fun <T> success(data: T): ToolResponse<T> = ToolResponse(true, data = data)
        fun <T> error(message: String): ToolResponse<T> = ToolResponse(false, error = message)
    }
}