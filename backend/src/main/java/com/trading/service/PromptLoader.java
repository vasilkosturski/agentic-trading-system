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

@Component
public class PromptLoader {

    private static final PropertyPlaceholderHelper PLACEHOLDER_HELPER = new PropertyPlaceholderHelper("{", "}");

    private static final Pattern SAFE_PATH_SEGMENT = Pattern.compile("[a-zA-Z0-9_]+");
    private static final Pattern UNRESOLVED_PLACEHOLDER = Pattern.compile("(?<!\\{)\\{[a-zA-Z0-9_]+}(?!})");

    public String loadBaseTemplate(String agentType) throws IOException {
        validatePathSegment(agentType, "agentType");
        return loadClasspathResource(String.format("prompts/%s/base.txt", agentType));
    }

    public String loadPersonalityFile(String agentType, String agentName) throws IOException {
        validatePathSegment(agentType, "agentType");
        validatePathSegment(agentName, "agentName");
        return loadClasspathResource(String.format("prompts/%s/%s.txt", agentType, agentName.toLowerCase()));
    }

    /**
     * Format:
     *   key: single-line value
     *   key:
     *   multi-line value
     *   continues here
     */
    public Map<String, String> parsePersonalityFields(String content) {
        Map<String, String> fields = new HashMap<>();
        String currentKey = null;
        StringBuilder currentValue = new StringBuilder();

        for (String line : content.split("\n")) {
            int colonPos = line.indexOf(':');

            if (colonPos > 0
                    && SAFE_PATH_SEGMENT.matcher(line.substring(0, colonPos)).matches()) {
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
                if (currentKey != null) {
                    if (currentValue.length() > 0) {
                        currentValue.append("\n");
                    }
                    currentValue.append(line);
                }
            }
        }

        if (currentKey != null) {
            fields.put(currentKey, currentValue.toString().trim());
        }

        return fields;
    }

    public String composePrompt(String agentType, String agentName) throws IOException {
        String baseTemplate = loadBaseTemplate(agentType);
        String personalityContent = loadPersonalityFile(agentType, agentName.toLowerCase());
        Map<String, String> personalityFields = parsePersonalityFields(personalityContent);

        String result = PLACEHOLDER_HELPER.replacePlaceholders(baseTemplate, personalityFields::get);

        if (UNRESOLVED_PLACEHOLDER.matcher(result).find()) {
            throw new IllegalStateException(String.format(
                    "Unresolved single-brace placeholders found in prompt for %s/%s. "
                            + "Check that personality file defines all required fields.",
                    agentType, agentName));
        }

        return result;
    }

    private String loadClasspathResource(String path) throws IOException {
        ClassPathResource resource = new ClassPathResource(path);

        if (!resource.exists()) {
            throw new IOException("Resource not found: " + path);
        }

        return StreamUtils.copyToString(resource.getInputStream(), StandardCharsets.UTF_8);
    }

    /**
     * Prevents path traversal attacks via agentType or agentName parameters.
     */
    private void validatePathSegment(String value, String paramName) {
        if (value == null || !SAFE_PATH_SEGMENT.matcher(value).matches()) {
            throw new IllegalArgumentException(
                    String.format("Invalid %s: must contain only alphanumeric characters and underscores", paramName));
        }
    }
}
