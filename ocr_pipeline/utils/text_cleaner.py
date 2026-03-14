"""
Text cleaning utilities for OCR output.

Handles common OCR artifacts: extra whitespace, broken lines, encoding
issues, and structural noise. Designed to produce clean text suitable
for downstream LLM extraction.
"""

import re
import unicodedata
from ocr_pipeline.models import CleanedText


def clean_ocr_text(raw_text: str) -> CleanedText:
    """
    Clean raw OCR text through a multi-step pipeline.

    Steps:
        1. Normalize unicode characters
        2. Fix common OCR character substitutions
        3. Remove control characters
        4. Normalize whitespace and line breaks
        5. Remove page artifacts (headers/footers/page numbers)
        6. Fix broken words from line wrapping
        7. Collapse excessive blank lines

    Args:
        raw_text: Raw text from Textract OCR.

    Returns:
        CleanedText with the processed text and basic stats.
    """
    if not raw_text or not raw_text.strip():
        return CleanedText(text="", line_count=0, word_count=0)

    text = raw_text

    # Step 1: Unicode normalization (NFKC handles ligatures and compatibility chars)
    text = unicodedata.normalize("NFKC", text)

    # Step 2: Fix common OCR misreads
    text = _fix_ocr_substitutions(text)

    # Step 3: Remove control characters (keep newlines, tabs, spaces)
    text = _remove_control_characters(text)

    # Step 4: Normalize whitespace
    text = _normalize_whitespace(text)

    # Step 5: Remove page artifacts
    text = _remove_page_artifacts(text)

    # Step 6: Fix broken words from line-wrap hyphenation
    text = _fix_broken_words(text)

    # Step 7: Collapse excessive blank lines (max 2 consecutive)
    text = _collapse_blank_lines(text)

    # Final trim
    text = text.strip()

    lines = [l for l in text.split("\n") if l.strip()]
    words = text.split()

    return CleanedText(
        text=text,
        line_count=len(lines),
        word_count=len(words),
    )


def _fix_ocr_substitutions(text: str) -> str:
    """Fix common OCR character misreads."""
    replacements = {
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2026": "...", # ellipsis
        "\u00a0": " ",   # non-breaking space
        "\ufeff": "",    # BOM
        "\u200b": "",    # zero-width space
        "\u200c": "",    # zero-width non-joiner
        "\u200d": "",    # zero-width joiner
        "\uf0b7": "-",   # bullet character (common in Word docs)
        "\uf0a7": "-",   # section mark rendered as bullet
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _remove_control_characters(text: str) -> str:
    """Remove control characters except whitespace."""
    return "".join(
        ch for ch in text
        if ch in ("\n", "\t", " ") or not unicodedata.category(ch).startswith("C")
    )


def _normalize_whitespace(text: str) -> str:
    """Normalize tabs to spaces and collapse multiple spaces on each line."""
    text = text.replace("\t", "    ")
    # Collapse multiple spaces within lines (preserve newlines)
    lines = text.split("\n")
    lines = [re.sub(r" {2,}", " ", line) for line in lines]
    return "\n".join(lines)


def _remove_page_artifacts(text: str) -> str:
    """Remove common page headers, footers, and page numbers."""
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        # Skip standalone page numbers
        if re.match(r"^(Page\s*)?\d{1,3}(\s*of\s*\d{1,3})?$", stripped, re.IGNORECASE):
            continue
        # Skip lines that are just dashes or underscores (decorative separators)
        if re.match(r"^[-_=]{5,}$", stripped):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def _fix_broken_words(text: str) -> str:
    """Rejoin words broken by end-of-line hyphenation."""
    # Pattern: word fragment + hyphen + newline + continuation
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    return text


def _collapse_blank_lines(text: str) -> str:
    """Collapse runs of 3+ blank lines down to 2."""
    return re.sub(r"\n{3,}", "\n\n", text)


def extract_sections(text: str) -> dict[str, str]:
    """
    Attempt to split cleaned text into labeled sections.

    Useful for resumes where headings like 'Experience', 'Education',
    'Skills' are present. Returns a dict mapping section names to their
    content. Falls back to {"full_text": text} if no sections found.
    """
    # Common resume/JD section headings
    section_pattern = re.compile(
        r"^(EXPERIENCE|EDUCATION|SKILLS|SUMMARY|OBJECTIVE|PROJECTS|"
        r"CERTIFICATIONS|QUALIFICATIONS|REQUIREMENTS|RESPONSIBILITIES|"
        r"ABOUT|OVERVIEW|DESCRIPTION|BENEFITS|COMPENSATION|"
        r"TECHNICAL\s+SKILLS|WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|"
        r"KEY\s+RESPONSIBILITIES|PREFERRED\s+QUALIFICATIONS|"
        r"REQUIRED\s+QUALIFICATIONS|WHAT\s+YOU.LL\s+DO|WHO\s+YOU\s+ARE)"
        r"\s*:?\s*$",
        re.IGNORECASE | re.MULTILINE,
    )

    matches = list(section_pattern.finditer(text))

    if not matches:
        return {"full_text": text}

    sections: dict[str, str] = {}

    # Capture text before the first section heading
    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections["header"] = preamble

    for i, match in enumerate(matches):
        section_name = match.group(1).strip().lower().replace(" ", "_")
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        content = text[start:end].strip()
        if content:
            sections[section_name] = content

    return sections