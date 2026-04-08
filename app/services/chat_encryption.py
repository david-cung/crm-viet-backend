import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import settings


def _key_bytes() -> bytes:
    raw = (settings.chat_encryption_key or "").strip()
    if not raw:
        raise ValueError("CHAT_ENCRYPTION_KEY is not set")
    try:
        key = bytes.fromhex(raw)
    except ValueError as e:  # noqa: BLE001
        raise ValueError("CHAT_ENCRYPTION_KEY must be 32-byte hex") from e
    if len(key) != 32:
        raise ValueError("CHAT_ENCRYPTION_KEY must be 32 bytes (64 hex chars)")
    return key


def encrypt_message(plaintext: str) -> tuple[str, str, str]:
    key = _key_bytes()
    aes = AESGCM(key)
    nonce = os.urandom(12)
    ct_and_tag = aes.encrypt(nonce, plaintext.encode("utf-8"), None)
    # cryptography returns ciphertext || tag (tag is 16 bytes)
    ciphertext = ct_and_tag[:-16]
    tag = ct_and_tag[-16:]
    return (
        base64.b64encode(ciphertext).decode("ascii"),
        base64.b64encode(nonce).decode("ascii"),
        base64.b64encode(tag).decode("ascii"),
    )


def decrypt_message(ciphertext_b64: str, iv_b64: str, tag_b64: str) -> str:
    key = _key_bytes()
    aes = AESGCM(key)
    ciphertext = base64.b64decode(ciphertext_b64)
    nonce = base64.b64decode(iv_b64)
    tag = base64.b64decode(tag_b64)
    pt = aes.decrypt(nonce, ciphertext + tag, None)
    return pt.decode("utf-8")

