#!/usr/bin/env python3
"""Shared deprecated foundation token patterns for HostFlow FOUNDATION_V1 enforcement."""

from __future__ import annotations

import re
from dataclasses import dataclass

SRC_SUFFIXES = (".ts", ".tsx", ".js", ".jsx", ".css")

SPACING = re.compile(
    r"\b(?:p|px|py|pt|pr|pb|pl|m|mx|my|mt|mr|mb|ml|gap|gap-x|gap-y)"
    r"-(?:1\.5|2\.5|3\.5|5|7|16|20|24|32|96)\b"
    r"|\b(?:gap|p|py|pt|pr|pb|pl|m|mx|my|mt|mr|mb|ml)-px\b"
)

TYPOGRAPHY = re.compile(
    r"\b(?:text-4xl|text-6xl|leading-snug|leading-[456])\b"
)

COLORS = re.compile(
    r"\b(?:text|bg|border|ring|from|to|via|fill|stroke|outline|decoration|divide|placeholder|accent|caret)"
    r"-(?:gray|green|teal|red|yellow|orange|sky|indigo|violet|purple|cyan)"
    r"(?:-\d{2,3})?(?:/\d+)?\b"
)

RADIUS = re.compile(r"\brounded-(?:md|2xl)\b")

SHADOW = re.compile(r"\bshadow\b(?!-)|\bshadow-(?:lg|2xl|inner)\b")

BREAKPOINTS = re.compile(r"\b2xl:")

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("spacing", SPACING),
    ("typography", TYPOGRAPHY),
    ("colors", COLORS),
    ("radius", RADIUS),
    ("shadow", SHADOW),
    ("breakpoints", BREAKPOINTS),
]

ALLOW_MARKER = "foundation-allow"
# Requires "foundation-allow: <reason>" with at least MIN_ALLOW_REASON_LEN chars of reason.
MIN_ALLOW_REASON_LEN = 8
ALLOW_REASON = re.compile(
    rf"{re.escape(ALLOW_MARKER)}:\s*(.{{{MIN_ALLOW_REASON_LEN},}})"
)


@dataclass(frozen=True)
class Finding:
    category: str
    token: str
    file: str
    line: int
    snippet: str


def allow_reason(line: str) -> str | None:
    match = ALLOW_REASON.search(line)
    if not match:
        return None
    return match.group(1).strip()


def line_suppressed(line: str, previous: str) -> bool:
    if allow_reason(line):
        return True
    if allow_reason(previous):
        return True
    return False


def invalid_allow_lines(text: str, file: str = "") -> list[Finding]:
    """Lines that mention foundation-allow without a valid reason (diff enforcement)."""
    findings: list[Finding] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if ALLOW_MARKER not in line:
            continue
        if allow_reason(line):
            continue
        findings.append(
            Finding(
                category="allow",
                token=ALLOW_MARKER,
                file=file,
                line=i,
                snippet=line.strip()[:160],
            )
        )
    return findings


def scrub_suppressed_lines(text: str) -> str:
    lines = text.splitlines()
    out: list[str] = []
    for i, line in enumerate(lines):
        prev = lines[i - 1] if i else ""
        if line_suppressed(line, prev):
            out.append("")
        else:
            out.append(line)
    return "\n".join(out)


def find_in_text(text: str, file: str = "") -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    for i, line in enumerate(lines, start=1):
        prev = lines[i - 2] if i > 1 else ""
        if line_suppressed(line, prev):
            continue
        for category, pattern in PATTERNS:
            for match in pattern.finditer(line):
                findings.append(
                    Finding(
                        category=category,
                        token=match.group(0),
                        file=file,
                        line=i,
                        snippet=line.strip()[:160],
                    )
                )
    return findings
