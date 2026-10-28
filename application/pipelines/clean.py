from __future__ import annotations

import re
import unicodedata

ZERO_WIDTH_AND_BOM_RE = re.compile(r"[\u200b\ufeff]")
LINE_END_HYPHENATION_RE = re.compile(r"(?<=\w)-\n(?=\w)")
HORIZONTAL_WHITESPACE_RE = re.compile(r"[^\S\r\n]+")

DEFAULT_HEADER_FOOTER_PATTERNS: tuple[str, ...] = (r"^OpenStax Biology 2e$",)


def clean_source_text(raw_text: str, furniture: set[str] | None = None) -> str:
    # NFC preserves mathematical superscripts and symbols that NFKC can change.
    text = unicodedata.normalize("NFC", raw_text or "")
    text = ZERO_WIDTH_AND_BOM_RE.sub("", text)
    text = text.replace("\u00ad\r\n", "").replace("\u00ad\n", "").replace("\u00ad", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    compiled_patterns = tuple(re.compile(pattern) for pattern in DEFAULT_HEADER_FOOTER_PATTERNS)

    lines: list[str] = []
    for raw_line in text.splitlines():
        line = HORIZONTAL_WHITESPACE_RE.sub(" ", raw_line).strip()
        if line and (
            line in (furniture or set())
            or any(pattern.fullmatch(line) for pattern in compiled_patterns)
        ):
            continue
        lines.append(line)

    text = "\n".join(lines)
    # A hard hyphen may be meaningful (e.g. well-known). Preserve it, flag review
    # at the parser, and remove only the line break. Soft hyphens above are safe.
    text = LINE_END_HYPHENATION_RE.sub("-", text)

    paragraphs: list[str] = []
    for paragraph in re.split(r"\n\s*\n+", text.strip()):
        cleaned_paragraph = HORIZONTAL_WHITESPACE_RE.sub(" ", paragraph.replace("\n", " ")).strip()
        if cleaned_paragraph:
            paragraphs.append(cleaned_paragraph)

    return "\n\n".join(paragraphs)
