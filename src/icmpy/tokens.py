def estimate_tokens(text: str) -> int:
    """Return an approximate token count for *text*.

    Uses a simple heuristic: split on whitespace and multiply by ~1.3.
    This is accurate enough for ICM context-window budgeting without pulling
    in a tokenizer library.
    """
    if not text:
        return 0
    return max(1, int(len(text.split()) * 1.3))
