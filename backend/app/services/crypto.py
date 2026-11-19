import os

from cryptography.fernet import Fernet, InvalidToken


class EncryptionNotConfigured(Exception):
    """Server configuration error: The token encryption key is missing or invalid"""


def _fernet() -> Fernet:
    key = os.environ.get("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise EncryptionNotConfigured("TOKEN_ENCRYPTION_KEY is not set")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise EncryptionNotConfigured("TOKEN_ENCRYPTION_KEY is not a valid Fernet key") from exc


def encrypt_secret(plaintext: str) -> str:
  
    if not plaintext:
        raise ValueError("plaintext must be a non-empty string")
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str | None) -> str | None:
   
    if not ciphertext:
        return None
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        return None