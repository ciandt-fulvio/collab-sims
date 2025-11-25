"""
Unit tests for core utility functions.

Tests the utility functions in collab_sims.core.utils without requiring
any external dependencies or integrations.
"""


from collab_sims.core.utils import truncate_session_name


class TestTruncateSessionName:
    """Test session name truncation logic."""

    def test_short_text_returned_as_is(self):
        """Text shorter than max_length should be returned unchanged."""
        short_text = "Short text"
        result = truncate_session_name(short_text)
        assert result == "Short text"
        assert len(result) == 10

    def test_exactly_max_length(self):
        """Text exactly at max_length should be returned as-is."""
        text = "This is exactly thirty char"  # 27 chars
        result = truncate_session_name(text, max_length=27)
        assert result == text
        assert len(result) == 27

    def test_breaks_at_word_boundary_when_cutting_word(self):
        """Should look backward to find word boundary when cutting a word."""
        text = "This is more than thirty characters here"
        result = truncate_session_name(text, max_length=30)

        # Should stop at space before "characters" (not cut the word)
        assert result == "This is more than thirty"
        assert len(result) < 30
        assert not result.endswith("charact")  # Not cutting word

    def test_breaks_at_space(self):
        """Should stop at space character."""
        text = "Let me implement something really important and useful today"
        result = truncate_session_name(text, max_length=30)

        # Should stop at a space, not cut a word
        assert result == "Let me implement something"
        assert len(result) < 30
        assert " " not in result[-5:]  # No trailing spaces

    def test_breaks_at_punctuation_period(self):
        """Should stop at period punctuation when looking backward."""
        text = "Start here. and more text continues now"
        result = truncate_session_name(text, max_length=30)

        # Should look back from position 30 and find punctuation
        assert "." in result
        assert len(result) <= 30

    def test_breaks_at_punctuation_comma(self):
        """Should stop at comma punctuation."""
        text = "Testing, this is a test"
        result = truncate_session_name(text, max_length=10)

        assert result == "Testing,"
        assert result.endswith(",")

    def test_breaks_at_punctuation_semicolon(self):
        """Should stop at semicolon punctuation."""
        text = "First part; second part here"
        result = truncate_session_name(text, max_length=15)

        assert result == "First part;"
        assert result.endswith(";")

    def test_breaks_at_punctuation_colon(self):
        """Should stop at colon punctuation."""
        text = "Example: test this function"
        result = truncate_session_name(text, max_length=10)

        assert result == "Example:"
        assert result.endswith(":")

    def test_strips_trailing_whitespace(self):
        """Should strip any trailing whitespace."""
        text = "This is some text    "
        result = truncate_session_name(text, max_length=20)

        assert not result.endswith(" ")
        assert result == "This is some text"

    def test_empty_string(self):
        """Should handle empty string."""
        result = truncate_session_name("")
        assert result == ""

    def test_none_input(self):
        """Should handle None input."""
        result = truncate_session_name(None)
        assert result is None or result == ""

    def test_only_one_word_longer_than_max(self):
        """Should handle a single long word."""
        text = "Supercalifragilisticexpialidocious"
        result = truncate_session_name(text, max_length=30)

        # No punctuation found, should return up to max_length
        assert len(result) == 30
        assert result == text[:30]  # First 30 characters

    def test_custom_max_length(self):
        """Should respect custom max_length parameter."""
        text = "This is a test with custom length"
        result = truncate_session_name(text, max_length=10)

        assert len(result) <= 10
        assert result == "This is a"

    def test_multiple_punctuation_marks(self):
        """Should stop at first punctuation when looking backward."""
        text = "Hello, world! This is a test."
        result = truncate_session_name(text, max_length=20)

        # Should find punctuation when looking backward from position 20
        assert "!" in result or "," in result

    def test_real_world_session_names(self):
        """Test with realistic session prompts."""
        prompts = [
            (
                "Help me create a new feature for user authentication",
                "Help me create a new feature",
            ),
            (
                "Fix the bug in the checkout process that causes errors",
                "Fix the bug in the checkout",
            ),
            (
                "Refactor the database queries for better performance",
                "Refactor the database queries",
            ),
            ("Write tests for the API endpoints", "Write tests for the API"),
        ]

        for prompt, expected_prefix in prompts:
            result = truncate_session_name(prompt, max_length=30)
            assert len(result) <= 30, f"Result too long: {result}"
            assert result.startswith(expected_prefix[:15]), (
                f"Expected to start with '{expected_prefix[:15]}', got '{result}'"
            )
            # Ensure no word is cut in the middle
            assert not any(
                result.endswith(partial)
                for partial in ["creat", "featur", "authe", "check", "proce", "databa", "quer"]
            )

    def test_preserves_punctuation_at_boundary(self):
        """Should include punctuation when it's at the boundary."""
        text = "First sentence. Second one."
        result = truncate_session_name(text, max_length=16)

        # Should stop at period after "sentence"
        assert result == "First sentence."
        assert result.endswith(".")

    def test_unicode_characters(self):
        """Should handle unicode characters correctly."""
        text = "Hello 世界! This is a test with émojis 🎉"
        result = truncate_session_name(text, max_length=20)

        # Should handle unicode without errors
        assert len(result) <= 20
        assert "Hello" in result

    def test_all_punctuation_types(self):
        """Should recognize various punctuation types."""
        punctuation_chars = [
            ".",
            ",",
            "!",
            "?",
            ";",
            ":",
            "-",
            '"',
            "'",
            "(",
            ")",
            "[",
            "]",
            "{",
            "}",
        ]

        for punct in punctuation_chars:
            # Create text like "Word1Word2<punct>Word3Word4Word5..."
            full_text = f"Word1Word2{punct}Word3Word4Word5Word6Word7"
            result = truncate_session_name(full_text, max_length=20)

            # Should recognize the punctuation and stop there (or before if another punct found)
            assert len(result) <= 20, f"Result too long for punctuation {punct}: {result}"
            # Should contain the punctuation somewhere (unless word before it is longer)
            if len(f"Word1Word2{punct}") <= 20:
                assert punct in result or len(result) < len(f"Word1Word2{punct}"), (
                    f"Should contain {punct} or be shorter: {result}"
                )
