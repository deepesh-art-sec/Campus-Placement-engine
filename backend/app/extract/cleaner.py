"""
Text and document cleaning utilities.
Normalises unicode, smart quotes, bullets, whitespace, and tabular text.
"""

from __future__ import annotations

import re
import unicodedata

# Unicode smart quote and bullet replacements
REPLACEMENTS: dict[str, str] = {
    "\u2018": "'",  # Left single quotation mark
    "\u2019": "'",  # Right single quotation mark
    "\u201c": '"',  # Left double quotation mark
    "\u201d": '"',  # Right double quotation mark
    "\u2014": " - ", # Em dash
    "\u2013": " - ", # En dash
    "\u2022": "*",  # Bullet
    "\u25cf": "*",  # Black circle bullet
    "\u25cb": "*",  # White circle bullet
    "\u25aa": "*",  # Black small square
    "\u2026": "...",# Ellipsis
    "\u00a0": " ",  # Non-breaking space
    "\u20b9": "INR ", # Indian Rupee symbol
    "\u20a8": "Rs. ", # Rs symbol
    "\t": " ",
}


def clean_text(raw_text: str) -> str:
    """
    Normalises raw text from PDFs, DOCX, emails, and pastes:
      - Normalises unicode NFKC
      - Replaces smart quotes, dashes, and bullet symbols
      - Standardizes newline characters and collapses extraneous horizontal whitespace
    """
    if not raw_text:
        return ""

    text = unicodedata.normalize("NFKC", raw_text)

    for k, v in REPLACEMENTS.items():
        text = text.replace(k, v)

    # Standardize newlines
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Clean per line
    cleaned_lines = []
    for line in text.split("\n"):
        clean_line = re.sub(r"[ ]+", " ", line).strip()
        cleaned_lines.append(clean_line)

    # Collapse multiple consecutive blank lines
    collapsed = re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned_lines))
    return collapsed.strip()


def extract_sentences(text: str) -> list[str]:
    """Splits text into sentences for exact provenance tracing."""
    lines = text.split("\n")
    sentences = []
    for line in lines:
        line_s = line.strip()
        if not line_s:
            continue
        # Split on sentence terminals while keeping numbering intact
        parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9*])", line_s)
        for p in parts:
            p_clean = p.strip()
            if p_clean:
                sentences.append(p_clean)
    return sentences
