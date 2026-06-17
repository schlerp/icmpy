from __future__ import annotations

import pytest

from icmpy.tokens import estimate_tokens


def test_estimate_tokens_returns_zero_for_empty() -> None:
    assert estimate_tokens("") == 0


def test_estimate_tokens_counts_words() -> None:
    # Simple heuristic: ~1.3 tokens per whitespace-delimited word
    text = "Hello world"
    assert estimate_tokens(text) == 2  # 2 words * 1.3 -> 2 when floored


def test_estimate_tokens_warns_threshold() -> None:
    # 8,000 tokens would be roughly 6,154 whitespace words
    words = ["word"] * 6154
    text = " ".join(words)
    assert estimate_tokens(text) >= 8000
