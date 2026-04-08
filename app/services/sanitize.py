import bleach


def sanitize_chat_text(text: str) -> str:
    # Keep plaintext-only; strip any tags.
    return bleach.clean(text or "", tags=[], attributes={}, strip=True).strip()

