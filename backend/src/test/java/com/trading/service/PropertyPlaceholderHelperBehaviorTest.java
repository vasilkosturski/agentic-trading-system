package com.trading.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.util.PropertyPlaceholderHelper;

import java.util.HashMap;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * Tests to verify PropertyPlaceholderHelper behavior for edge cases
 * relevant to our prompt template substitution.
 */
@DisplayName("PropertyPlaceholderHelper Behavior Tests")
class PropertyPlaceholderHelperBehaviorTest {

    @Test
    @DisplayName("preserves double-brace placeholders when using single-brace prefix")
    void preservesDoubleBracePlaceholders() {
        PropertyPlaceholderHelper helper = new PropertyPlaceholderHelper("{", "}");

        String template = "Hello {name}, time is {{datetime}}, max is {{position_sizing_pct}}%";
        Map<String, String> values = new HashMap<>();
        values.put("name", "Warren");

        String result = helper.replacePlaceholders(template, values::get);

        assertEquals("Hello Warren, time is {{datetime}}, max is {{position_sizing_pct}}%", result);
        assertTrue(result.contains("{{datetime}}"), "Double braces should be preserved");
        assertTrue(result.contains("{{position_sizing_pct}}"), "Double braces should be preserved");
    }

    @Test
    @DisplayName("handles missing placeholders gracefully by returning null from resolver")
    void handlesMissingPlaceholdersWithNullResolver() {
        PropertyPlaceholderHelper helper = new PropertyPlaceholderHelper("{", "}");

        String template = "Hello {name}, your role is {role}";
        Map<String, String> values = new HashMap<>();
        values.put("name", "Warren");
        // "role" is missing

        String result = helper.replacePlaceholders(template, values::get);

        // When resolver returns null, placeholder is left as-is
        assertEquals("Hello Warren, your role is {role}", result);
    }

    @Test
    @DisplayName("throws exception when missing placeholder and strict mode enabled")
    void throwsExceptionForMissingPlaceholderInStrictMode() {
        // ignoreUnresolvable=false means throw exception for missing placeholders
        PropertyPlaceholderHelper helper = new PropertyPlaceholderHelper("{", "}", null, false);

        String template = "Hello {name}, your role is {role}";
        Map<String, String> values = new HashMap<>();
        values.put("name", "Warren");
        // "role" is missing

        assertThrows(IllegalArgumentException.class, () -> {
            helper.replacePlaceholders(template, values::get);
        });
    }

    @Test
    @DisplayName("replaces all occurrences of same placeholder")
    void replacesAllOccurrencesOfSamePlaceholder() {
        PropertyPlaceholderHelper helper = new PropertyPlaceholderHelper("{", "}");

        String template = "{name} is a {type} investor. {name} follows {type} principles.";
        Map<String, String> values = new HashMap<>();
        values.put("name", "Warren");
        values.put("type", "value");

        String result = helper.replacePlaceholders(template, values::get);

        assertEquals("Warren is a value investor. Warren follows value principles.", result);
    }

    @Test
    @DisplayName("handles nested braces correctly - does not recurse")
    void handlesNestedBracesWithoutRecursion() {
        PropertyPlaceholderHelper helper = new PropertyPlaceholderHelper("{", "}");

        String template = "Value is {value}";
        Map<String, String> values = new HashMap<>();
        values.put("value", "contains {nested} placeholder");

        String result = helper.replacePlaceholders(template, values::get);

        // PropertyPlaceholderHelper does NOT recursively expand substituted values
        assertEquals("Value is contains {nested} placeholder", result);
        assertTrue(result.contains("{nested}"), "Nested placeholder should not be expanded");
    }

    @Test
    @DisplayName("handles empty placeholder gracefully")
    void handlesEmptyPlaceholder() {
        PropertyPlaceholderHelper helper = new PropertyPlaceholderHelper("{", "}");

        String template = "Empty {} placeholder";
        Map<String, String> values = new HashMap<>();

        String result = helper.replacePlaceholders(template, values::get);

        // Empty placeholder key "{}" is passed to resolver as empty string
        assertEquals("Empty {} placeholder", result);
    }

    @Test
    @DisplayName("handles special characters in placeholder keys")
    void handlesSpecialCharactersInKeys() {
        PropertyPlaceholderHelper helper = new PropertyPlaceholderHelper("{", "}");

        String template = "Value is {key_with_underscores}, also {key.with.dots}";
        Map<String, String> values = new HashMap<>();
        values.put("key_with_underscores", "value1");
        values.put("key.with.dots", "value2");

        String result = helper.replacePlaceholders(template, values::get);

        assertEquals("Value is value1, also value2", result);
    }
}
