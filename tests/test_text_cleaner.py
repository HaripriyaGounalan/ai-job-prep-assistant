"""Tests for text cleaning utilities."""

import pytest
from ocr_pipeline.utils.text_cleaner import (
    clean_ocr_text,
    extract_sections,
)


class TestCleanOCRText:
    def test_empty_input(self):
        result = clean_ocr_text("")
        assert result.text == ""
        assert result.word_count == 0

    def test_whitespace_only(self):
        result = clean_ocr_text("   \n\n  \t  ")
        assert result.text == ""

    def test_basic_cleaning(self):
        result = clean_ocr_text("Hello   World\nThis is  a   test")
        assert "Hello World" in result.text
        assert "This is a test" in result.text

    def test_unicode_normalization(self):
        # fi ligature → "fi"
        result = clean_ocr_text("proﬁle conﬁguration")
        assert "profile" in result.text
        assert "configuration" in result.text

    def test_smart_quotes_replaced(self):
        result = clean_ocr_text("\u201cHello\u201d and \u2018world\u2019")
        assert '"Hello"' in result.text
        assert "'world'" in result.text

    def test_page_numbers_removed(self):
        text = "Some content\nPage 3\nMore content\n2\nPage 5 of 10\nEnd"
        result = clean_ocr_text(text)
        assert "Page 3" not in result.text
        assert "Page 5 of 10" not in result.text
        assert "Some content" in result.text
        assert "End" in result.text

    def test_decorative_separators_removed(self):
        text = "Section A\n----------\nContent A"
        result = clean_ocr_text(text)
        assert "----------" not in result.text
        assert "Section A" in result.text
        assert "Content A" in result.text

    def test_broken_word_rejoining(self):
        text = "This is a hyph-\nenated word"
        result = clean_ocr_text(text)
        assert "hyphenated" in result.text

    def test_excessive_blank_lines_collapsed(self):
        text = "Line 1\n\n\n\n\nLine 2"
        result = clean_ocr_text(text)
        assert "\n\n\n" not in result.text
        assert "Line 1" in result.text
        assert "Line 2" in result.text

    def test_word_and_line_counts(self):
        text = "Hello world\nFoo bar baz"
        result = clean_ocr_text(text)
        assert result.word_count == 5
        assert result.line_count == 2

    def test_zero_width_characters_removed(self):
        result = clean_ocr_text("He\u200bllo W\u200corld")
        assert "Hello" in result.text
        assert "World" in result.text


class TestExtractSections:
    def test_no_sections_found(self):
        result = extract_sections("Just some plain text without headings.")
        assert "full_text" in result

    def test_resume_sections(self):
        text = (
            "John Doe\njohn@email.com\n\n"
            "EXPERIENCE\n"
            "Software Engineer at Acme Corp\n"
            "Built things\n\n"
            "EDUCATION\n"
            "BS Computer Science, MIT\n\n"
            "SKILLS\n"
            "Python, AWS, Docker"
        )
        sections = extract_sections(text)
        assert "experience" in sections
        assert "education" in sections
        assert "skills" in sections
        assert "Acme Corp" in sections["experience"]

    def test_header_preamble_captured(self):
        text = (
            "Jane Smith\n555-0100\n\n"
            "SUMMARY\n"
            "Experienced developer"
        )
        sections = extract_sections(text)
        assert "header" in sections
        assert "Jane Smith" in sections["header"]