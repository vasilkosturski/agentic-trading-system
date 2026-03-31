package com.trading.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.io.IOException;

import static org.junit.jupiter.api.Assertions.*;

@DisplayName("PromptLoader Tests")
class PromptLoaderTest {

    @Test
    @DisplayName("loads base template from classpath")
    void loadsBaseTemplateFromClasspath() throws IOException {
        PromptLoader loader = new PromptLoader();

        String template = loader.loadBaseTemplate("decision_maker");

        assertNotNull(template, "Base template should not be null");
        assertTrue(template.contains("{identity_line}"), "Template should contain identity_line placeholder");
        assertTrue(template.contains("{identity}"), "Template should contain identity placeholder");
    }

    @Test
    @DisplayName("loads personality file from classpath")
    void loadsPersonalityFileFromClasspath() throws IOException {
        PromptLoader loader = new PromptLoader();

        String content = loader.loadPersonalityFile("decision_maker", "warren");

        assertNotNull(content, "Personality content should not be null");
        assertTrue(content.contains("identity_line:"), "Should contain identity_line field");
        assertTrue(content.contains("Warren Buffett"), "Should contain Warren Buffett reference");
    }

    @Test
    @DisplayName("parses personality file into key-value map")
    void parsesPersonalityFileIntoMap() {
        PromptLoader loader = new PromptLoader();
        String content = """
            identity_line: You are Warren, a Value Investor making trading decisions.

            identity: You are Warren, named in homage to Warren Buffett.

            decision_criteria:
            - BUY: Stock trades below intrinsic value
            - SELL: Position no longer meets value criteria
            """;

        var fields = loader.parsePersonalityFields(content);

        assertEquals("You are Warren, a Value Investor making trading decisions.", fields.get("identity_line"));
        assertEquals("You are Warren, named in homage to Warren Buffett.", fields.get("identity"));
        assertTrue(fields.get("decision_criteria").contains("BUY:"));
    }

    @Test
    @DisplayName("composes prompt by substituting personality into base template")
    void composesPromptBySubstitutingPersonality() throws IOException {
        PromptLoader loader = new PromptLoader();

        String composedPrompt = loader.composePrompt("decision_maker", "warren");

        assertNotNull(composedPrompt, "Composed prompt should not be null");
        assertTrue(composedPrompt.contains("Warren Buffett"), "Should contain Warren Buffett from personality");
        assertTrue(composedPrompt.contains("Value Investor"), "Should contain value investor style");
        assertFalse(composedPrompt.contains("{identity_line}"), "Should not contain unreplaced placeholders");
        assertFalse(composedPrompt.contains("{identity}"), "Should not contain unreplaced placeholders");
    }

    @Test
    @DisplayName("throws exception for missing base template")
    void throwsExceptionForMissingBaseTemplate() {
        PromptLoader loader = new PromptLoader();

        assertThrows(IOException.class, () -> {
            loader.loadBaseTemplate("nonexistent_type");
        });
    }

    @Test
    @DisplayName("throws exception for missing personality file")
    void throwsExceptionForMissingPersonalityFile() {
        PromptLoader loader = new PromptLoader();

        assertThrows(IOException.class, () -> {
            loader.loadPersonalityFile("decision_maker", "nonexistent");
        });
    }

    @Test
    @DisplayName("rejects path traversal in agentType")
    void rejectsPathTraversalInAgentType() {
        PromptLoader loader = new PromptLoader();

        assertThrows(IllegalArgumentException.class, () -> {
            loader.loadBaseTemplate("../secret");
        });
    }

    @Test
    @DisplayName("rejects path traversal in agentName")
    void rejectsPathTraversalInAgentName() {
        PromptLoader loader = new PromptLoader();

        assertThrows(IllegalArgumentException.class, () -> {
            loader.loadPersonalityFile("decision_maker", "../../application");
        });
    }

    @Test
    @DisplayName("rejects null agentType")
    void rejectsNullAgentType() {
        PromptLoader loader = new PromptLoader();

        assertThrows(IllegalArgumentException.class, () -> {
            loader.loadBaseTemplate(null);
        });
    }

    @Test
    @DisplayName("loads market_analyst base template from classpath")
    void loadsMarketAnalystBaseTemplate() throws IOException {
        PromptLoader loader = new PromptLoader();

        String template = loader.loadBaseTemplate("market_analyst");

        assertNotNull(template, "Market analyst base template should not be null");
        assertTrue(template.contains("{identity_line}"), "Template should contain identity_line placeholder");
        assertTrue(template.contains("{identity}"), "Template should contain identity placeholder");
        assertTrue(template.contains("**Your Mission:**"), "Template should contain mission section");
    }

    @Test
    @DisplayName("loads market_analyst personality file from classpath")
    void loadsMarketAnalystPersonalityFile() throws IOException {
        PromptLoader loader = new PromptLoader();

        String content = loader.loadPersonalityFile("market_analyst", "warren");

        assertNotNull(content, "Market analyst personality content should not be null");
        assertTrue(content.contains("identity_line:"), "Should contain identity_line field");
        assertTrue(content.contains("Market Analyst"), "Should contain Market Analyst reference");
    }

    @Test
    @DisplayName("composes market_analyst prompt by substituting personality")
    void composesMarketAnalystPrompt() throws IOException {
        PromptLoader loader = new PromptLoader();

        String composedPrompt = loader.composePrompt("market_analyst", "warren");

        assertNotNull(composedPrompt, "Composed market analyst prompt should not be null");
        assertTrue(composedPrompt.contains("Market Analyst"), "Should contain Market Analyst from personality");
        assertTrue(composedPrompt.contains("Warren"), "Should contain Warren reference");
        assertFalse(composedPrompt.contains("{identity_line}"), "Should not contain unreplaced identity_line placeholder");
        assertFalse(composedPrompt.contains("{identity}"), "Should not contain unreplaced identity placeholder");
    }
}
