package com.trading.controller

import com.trading.service.MarketService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/mcp/market")
class MarketController(
    private val marketService: MarketService
) {
    
    @PostMapping("/tools/lookup_share_price")
    fun lookupSharePrice(@RequestBody request: LookupSharePriceRequest): ResponseEntity<ToolResponse<Double>> {
        return try {
            val price = marketService.getSharePrice(request.symbol)
            ResponseEntity.ok(ToolResponse.success(price))
        } catch (e: Exception) {
            ResponseEntity.badRequest().body(ToolResponse.error(e.message ?: "Unknown error"))
        }
    }
    
    @GetMapping("/tools/list")
    fun listTools(): ResponseEntity<List<ToolDefinition>> {
        val tools = listOf(
            ToolDefinition(
                name = "lookup_share_price",
                description = "This tool provides the current price of the given stock symbol.",
                parameters = mapOf(
                    "symbol" to ParameterDefinition("string", "the symbol of the stock", true)
                )
            )
        )
        return ResponseEntity.ok(tools)
    }
}

// Request DTOs
data class LookupSharePriceRequest(val symbol: String)

// Tool definition for MCP discovery
data class ToolDefinition(
    val name: String,
    val description: String,
    val parameters: Map<String, ParameterDefinition>
)

data class ParameterDefinition(
    val type: String,
    val description: String,
    val required: Boolean
)