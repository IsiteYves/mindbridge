import base64
import os
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

FORMAT_PREFIX = "v1:"
NONCE_BYTES = 12
KEY_BYTES = 32


class EncryptionNotConfigured(Exception):
    """Server configuration error: The token encryption key is missing or invalid"""


def _aead() -> AESGCM:
    key = os.environ.get("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise EncryptionNotConfigured("TOKEN_ENCRYPTION_KEY is not set")
    try:
        raw = base64.urlsafe_b64decode(key.encode())
    except (ValueError, TypeError) as exc:
        raise EncryptionNotConfigured("TOKEN_ENCRYPTION_KEY is not valid base64") from exc
    if len(raw) != KEY_BYTES:
        raise EncryptionNotConfigured("TOKEN_ENCRYPTION_KEY must decode to 32 bytes")
    return AESGCM(raw)


def encrypt_secret(plaintext: str) -> str:
    if not plaintext:
        raise ValueError("plaintext must be a non-empty string")
    # Each encryption gets a fresh random nonce, stored in front of the ciphertext.
    nonce = secrets.token_bytes(NONCE_BYTES)
    sealed = _aead().encrypt(nonce, plaintext.encode(), None)
    return FORMAT_PREFIX + base64.urlsafe_b64encode(nonce + sealed).decode()


# Returns None for any malformed, tampered or wrong-key value instead of raising.
def decrypt_secret(ciphertext: str | None) -> str | None:
    if not ciphertext or not ciphertext.startswith(FORMAT_PREFIX):
        return None
    try:
        blob = base64.urlsafe_b64decode(ciphertext[len(FORMAT_PREFIX):].encode())
        return _aead().decrypt(blob[:NONCE_BYTES], blob[NONCE_BYTES:], None).decode()
    except (InvalidTag, ValueError, TypeError):
        return None
