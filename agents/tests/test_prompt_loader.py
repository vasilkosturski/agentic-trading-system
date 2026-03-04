"""Tests for prompt_loader: TOML-like parser, personality loading, and composition.

Covers:
1. _parse_personality_file() edge cases (single-line, multi-line, colons, blank lines)
2. load_personality() for all 8 personality files
3. load_composed_prompt() strict personality substitution
4. load_prompt_template() end-to-end composition
5. Missing personality field raises KeyError (strict validation)
"""

import pytest

from prompt_loader import (
    _parse_personality_file,
    load_personality,
    load_base_template,
    load_composed_prompt,
    load_prompt_template,
    format_prompt,
    VALID_AGENT_NAMES,
)


# ============================================================================
# 1. _parse_personality_file() parser tests
# ============================================================================


class TestParsePersonalityFile:
    """Test the custom TOML-like personality parser."""

    def test_single_line_value(self):
        """Single key: value on the same line."""
        content = "name: Warren"
        result = _parse_personality_file(content)
        assert result == {"name": "Warren"}

    def test_multiple_single_line_values(self):
        """Multiple single-line key-value pairs."""
        content = "name: Warren\nstyle: value investing"
        result = _parse_personality_file(content)
        assert result == {"name": "Warren", "style": "value investing"}

    def test_multi_line_value(self):
        """Value that spans multiple lines."""
        content = "criteria:\n- Strong moats\n- High ROE\n- Low debt"
        result = _parse_personality_file(content)
        assert result["criteria"] == "- Strong moats\n- High ROE\n- Low debt"

    def test_colon_in_value(self):
        """Colons within a value should not start a new key."""
        content = "hint: Search for: value stocks, undervalued companies"
        result = _parse_personality_file(content)
        assert result["hint"] == "Search for: value stocks, undervalued companies"

    def test_blank_line_stripping(self):
        """Leading/trailing blank lines in multi-line values are stripped."""
        content = "description:\n\nFirst paragraph.\n\nSecond paragraph.\n\n"
        result = _parse_personality_file(content)
        assert result["description"] == "First paragraph.\n\nSecond paragraph."

    def test_empty_value(self):
        """Key with no value results in empty string."""
        content = "empty_field:\nnext_key: has value"
        result = _parse_personality_file(content)
        assert result["empty_field"] == ""
        assert result["next_key"] == "has value"

    def test_underscored_keys(self):
        """Keys with underscores are parsed correctly."""
        content = "identity_line: You are Warren\nresearch_step_title: Research value"
        result = _parse_personality_file(content)
        assert result["identity_line"] == "You are Warren"
        assert result["research_step_title"] == "Research value"

    def test_empty_content(self):
        """Empty content returns empty dict."""
        result = _parse_personality_file("")
        assert result == {}

    def test_preserves_internal_indentation(self):
        """Internal indentation within multi-line values is preserved."""
        content = "bullets:\n   - First item\n   - Second item\n   - Third item"
        result = _parse_personality_file(content)
        assert "   - First item" in result["bullets"]
        assert "   - Second item" in result["bullets"]

    def test_multi_line_value_between_keys(self):
        """Multi-line value is captured correctly between two keys."""
        content = (
            "first: single\n"
            "second:\n"
            "line one\n"
            "line two\n"
            "third: after"
        )
        result = _parse_personality_file(content)
        assert result["first"] == "single"
        assert result["second"] == "line one\nline two"
        assert result["third"] == "after"


# ============================================================================
# 2. load_personality() - all 8 personality files parse correctly
# ============================================================================


class TestLoadPersonality:
    """Test loading real personality files from disk."""

    @pytest.mark.parametrize(
        "agent_type,agent_name",
        [
            ("market_analyst", "warren"),
            ("market_analyst", "george"),
            ("market_analyst", "ray"),
            ("market_analyst", "cathie"),
            ("decision_maker", "warren"),
            ("decision_maker", "george"),
            ("decision_maker", "ray"),
            ("decision_maker", "cathie"),
        ],
    )
    def test_all_personality_files_parse(self, agent_type, agent_name):
        """Every personality file parses without error and returns non-empty dict."""
        fields = load_personality(agent_type, agent_name)
        assert isinstance(fields, dict)
        assert len(fields) > 0, f"No fields parsed from {agent_type}/{agent_name}"

    @pytest.mark.parametrize("agent_type", ["market_analyst", "decision_maker"])
    def test_required_keys_present(self, agent_type):
        """Every personality file has the mandatory identity keys."""
        required_keys = {"identity_line", "identity"}
        for name in VALID_AGENT_NAMES:
            fields = load_personality(agent_type, name)
            missing = required_keys - set(fields.keys())
            assert not missing, (
                f"{agent_type}/{name} missing required keys: {missing}"
            )

    def test_invalid_agent_name_raises(self):
        """Invalid agent name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid agent name"):
            load_personality("market_analyst", "invalid_agent")

    def test_case_insensitive_name(self):
        """Agent names are case-insensitive."""
        fields_lower = load_personality("market_analyst", "warren")
        fields_upper = load_personality("market_analyst", "Warren")
        assert fields_lower == fields_upper


# ============================================================================
# 3. load_composed_prompt() strict composition
# ============================================================================


class TestLoadComposedPrompt:
    """Test composed prompt generation with strict substitution."""

    @pytest.mark.parametrize(
        "agent_type,agent_name",
        [
            ("market_analyst", "warren"),
            ("market_analyst", "george"),
            ("market_analyst", "ray"),
            ("market_analyst", "cathie"),
            ("decision_maker", "warren"),
            ("decision_maker", "george"),
            ("decision_maker", "ray"),
            ("decision_maker", "cathie"),
        ],
    )
    def test_composes_without_unresolved_personality_placeholders(
        self, agent_type, agent_name
    ):
        """Composed prompt has no unresolved personality placeholders.

        After strict substitution, the only remaining {placeholder} should be
        runtime ones like {datetime}.
        """
        composed = load_composed_prompt(agent_type, agent_name)
        assert isinstance(composed, str)
        assert len(composed) > 100  # Sanity check: non-trivial output

        # Verify no personality keys remain unresolved
        personality = load_personality(agent_type, agent_name)
        for key in personality:
            assert f"{{{key}}}" not in composed, (
                f"Unresolved personality placeholder '{{{key}}}' found in composed prompt"
            )

    @pytest.mark.parametrize("agent_type", ["market_analyst", "decision_maker"])
    def test_datetime_placeholder_preserved(self, agent_type):
        """Runtime {datetime} placeholder is preserved after personality substitution."""
        composed = load_composed_prompt(agent_type, "warren")
        assert "{datetime}" in composed, (
            "Runtime {datetime} placeholder should be preserved for format_prompt()"
        )

    def test_missing_personality_field_raises_key_error(self, tmp_path):
        """Missing personality key in base template raises KeyError."""
        import prompt_loader

        # Save original PROMPTS_DIR
        original_dir = prompt_loader.PROMPTS_DIR

        try:
            # Create test files with a missing key
            agent_dir = tmp_path / "market_analyst"
            agent_dir.mkdir()

            # Base template references {missing_key}
            base = agent_dir / "base.txt"
            base.write_text("{identity_line}\n{missing_key}\n")

            # Personality only has identity_line
            personality = agent_dir / "warren.personality.txt"
            personality.write_text("identity_line: Hello\n")

            # Override PROMPTS_DIR
            prompt_loader.PROMPTS_DIR = tmp_path

            with pytest.raises(KeyError, match="missing_key"):
                load_composed_prompt("market_analyst", "warren")
        finally:
            prompt_loader.PROMPTS_DIR = original_dir


# ============================================================================
# 4. load_prompt_template() end-to-end
# ============================================================================


class TestLoadPromptTemplate:
    """Test end-to-end template loading."""

    def test_end_to_end_composition(self):
        """load_prompt_template returns a valid template for all agents."""
        template = load_prompt_template("market_analyst", "Warren")
        assert isinstance(template, str)
        assert len(template) > 100
        # Should still have {datetime} for runtime
        assert "{datetime}" in template

    def test_invalid_agent_name_raises(self):
        """Invalid agent name raises ValueError."""
        with pytest.raises(ValueError, match="Invalid agent name"):
            load_prompt_template("market_analyst", "NotAnAgent")

    def test_format_prompt_resolves_datetime(self):
        """format_prompt() resolves the {datetime} placeholder."""
        template = load_prompt_template("market_analyst", "Warren")
        formatted = format_prompt(template, datetime="2025-06-15 10:00:00")
        assert "{datetime}" not in formatted
        assert "2025-06-15 10:00:00" in formatted

    def test_format_prompt_auto_datetime(self):
        """format_prompt() auto-fills datetime if not provided."""
        template = load_prompt_template("decision_maker", "George")
        formatted = format_prompt(template)
        assert "{datetime}" not in formatted


# ============================================================================
# 5. Strict validation: missing personality field
# ============================================================================


class TestStrictValidation:
    """Test that strict personality substitution catches missing keys."""

    def test_partial_format_dict_still_used_in_format_prompt(self):
        """format_prompt() uses _PartialFormatDict for runtime (graceful for unknown keys)."""
        # Template with an unknown runtime placeholder
        template = "Hello {name}, today is {datetime}"
        result = format_prompt(template, datetime="2025-01-01")
        # {name} should be preserved (not crash)
        assert "{name}" in result
        assert "2025-01-01" in result

    def test_composed_prompt_is_valid_for_format_prompt(self):
        """Composed prompt can be passed to format_prompt() without errors."""
        for agent_type in ["market_analyst", "decision_maker"]:
            for name in VALID_AGENT_NAMES:
                template = load_composed_prompt(agent_type, name)
                # Should not raise -- only {datetime} remains
                result = format_prompt(template, datetime="2025-01-01 12:00:00")
                assert "2025-01-01 12:00:00" in result
