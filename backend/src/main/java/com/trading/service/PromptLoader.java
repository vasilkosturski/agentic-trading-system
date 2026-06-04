package com.trading.service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Pattern;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Component;
import org.springframework.util.PropertyPlaceholderHelper;
import org.springframework.util.StreamUtils;

/**
 * Loads and composes agent system prompts from classpath resources.
 * Reads base template and personality files, then substitutes personality fields into template.
 */
@Component
public class PromptLoader {

    private static final PropertyPlaceholderHelper PLACEHOLDER_HELPER = new PropertyPlaceholderHelper("{", "}");

    private static final Pattern SAFE_PATH_SEGMENT = Pattern.compile("[a-zA-Z0-9_]+");
    private static final Pattern UNRESOLVED_PLACEHOLDER = Pattern.compile("(?<!\\{)\\{[a-zA-Z0-9_]+}(?!})");

    /**
     * Load base template for an agent type from classpath.
     *
     * @param agentType Agent type (e.g., "decision_maker")
     * @return Base template content with placeholders
     * @throws IOException If template file not found or cannot be read
     */
    public String loadBaseTemplate(String agentType) throws IOException {
        validatePathSegment(agentType, "agentType");
        return loadClasspathResource(String.format("prompts/%s/base.txt", agentType));
    }

    /**
     * Load personality file for an agent from classpath.
     *
     * @param agentType Agent type (e.g., "decision_maker")
     * @param agentName Agent name (e.g., "warren")
     * @return Raw personality file content
     * @throws IOException If personality file not found or cannot be read
     */
    public String loadPersonalityFile(String agentType, String agentName) throws IOException {
        validatePathSegment(agentType, "agentType");
        validatePathSegment(agentName, "agentName");
        return loadClasspathResource(String.format("prompts/%s/%s.txt", agentType, agentName.toLowerCase()));
    }

    /**
     * Parse personality file content into key-value map.
     *
     * Format:
     *   key: single-line value
     *   key:
     *   multi-line value
     *   continues here
     *
     * @param content Raw personality file content
     * @return Map of field names to values
     */
    public Map<String, String> parsePersonalityFields(String content) {
        Map<String, String> fields = new HashMap<>();
        String currentKey = null;
        StringBuilder currentValue = new StringBuilder();

        for (String line : content.split("\n")) {
            int colonPos = line.indexOf(':');

            // Check if line starts a new key (word chars + colon)
            if (colonPos > 0
                    && SAFE_PATH_SEGMENT.matcher(line.substring(0, colonPos)).matches()) {
                // Save previous key if exists
                if (currentKey != null) {
                    fields.put(currentKey, currentValue.toString().trim());
                }

                currentKey = line.substring(0, colonPos).trim();
                String valueStart = line.substring(colonPos + 1);

                if (valueStart.trim().isEmpty()) {
                    currentValue = new StringBuilder();
                } else {
                    currentValue = new StringBuilder(valueStart.stripLeading());
                }
            } else {
                // Continuation of current key's value
                if (currentKey != null) {
                    if (currentValue.length() > 0) {
                        currentValue.append("\n");
                    }
                    currentValue.append(line);
                }
            }
        }

        // Save last key
        if (currentKey != null) {
            fields.put(currentKey, currentValue.toString().trim());
        }

        return fields;
    }

    /**
     * Compose full prompt by substituting personality fields into base template.
     * Uses Spring PropertyPlaceholderHelper for efficient single-pass O(n+m) substitution.
     *
     * Single-brace placeholders {key} are replaced with personality field values.
     * Double-brace placeholders {{key}} are preserved for later runtime substitution.
     *
     * @param agentType Agent type (e.g., "decision_maker")
     * @param agentName Agent name (e.g., "warren")
     * @return Composed prompt with personality substituted
     * @throws IOException If base template or personality file cannot be loaded
     * @throws IllegalStateException If required personality fields are missing
     */
    public String composePrompt(String agentType, String agentName) throws IOException {
        String baseTemplate = loadBaseTemplate(agentType);
        String personalityContent = loadPersonalityFile(agentType, agentName.toLowerCase());
        Map<String, String> personalityFields = parsePersonalityFields(personalityContent);

        String result = PLACEHOLDER_HELPER.replacePlaceholders(baseTemplate, personalityFields::get);

        // Validate no single-brace placeholders remain (double-braces are OK for runtime substitution)
        if (UNRESOLVED_PLACEHOLDER.matcher(result).find()) {
            throw new IllegalStateException(String.format(
                    "Unresolved single-brace placeholders found in prompt for %s/%s. "
                            + "Check that personality file defines all required fields.",
                    agentType, agentName));
        }

        return result;
    }

    /**
     * Load a classpath resource as a UTF-8 string.
     *
     * @param path Classpath resource path
     * @return File content as string
     * @throws IOException If resource not found or cannot be read
     */
    private String loadClasspathResource(String path) throws IOException {
        ClassPathResource resource = new ClassPathResource(path);

        if (!resource.exists()) {
            throw new IOException("Resource not found: " + path);
        }

        return StreamUtils.copyToString(resource.getInputStream(), StandardCharsets.UTF_8);
    }

    /**
     * Validate that a path segment contains only safe characters (alphanumeric and underscore).
     * Prevents path traversal attacks via agentType or agentName parameters.
     *
     * @param value The path segment to validate
     * @param paramName Parameter name for error messages
     * @throws IllegalArgumentException If value contains unsafe characters
     */
    private void validatePathSegment(String value, String paramName) {
        if (value == null || !SAFE_PATH_SEGMENT.matcher(value).matches()) {
            throw new IllegalArgumentException(
                    String.format("Invalid %s: must contain only alphanumeric characters and underscores", paramName));
        }
    }
}
