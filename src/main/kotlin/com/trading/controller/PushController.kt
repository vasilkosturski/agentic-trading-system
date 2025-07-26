package com.trading.controller

import com.trading.service.PushService
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*

@RestController
@RequestMapping("/mcp/push")
class PushController(
    private val pushService: PushService
) {
    
    @PostMapping("/tools/push")
    fun push(@RequestBody request: PushRequest): ResponseEntity<ToolResponse<String>> {
        return try {
            val result = pushService.sendPushNotification(request.message)
            ResponseEntity.ok(ToolResponse.success(result))
        } catch (e: Exception) {
            ResponseEntity.badRequest().body(ToolResponse.error(e.message ?: "Unknown error"))
        }
    }
    
    @GetMapping("/tools/list")
    fun listTools(): ResponseEntity<List<ToolDefinition>> {
        val tools = listOf(
            ToolDefinition(
                name = "push",
                description = "Send a push notification with this brief message",
                parameters = mapOf(
                    "message" to ParameterDefinition("string", "A brief message to push", true)
                )
            )
        )
        return ResponseEntity.ok(tools)
    }
}

// Request DTOs
data class PushRequest(val message: String)