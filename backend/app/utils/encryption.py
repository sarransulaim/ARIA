import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.core.config import settings
from app.core.exceptions import EncryptionError

_NONCE_SIZE = 12  # 96 bits — standard GCM nonce length


def _get_key() -> bytes:
    try:
        key = base64.b64decode(settings.encryption_key)
    except Exception as exc:
        raise EncryptionError(f"Encryption key is not valid base64: {exc}")
    if len(key) != 32:
        raise EncryptionError(
            f"Encryption key must decode to 32 bytes (AES-256); got {len(key)} bytes"
        )
    return key


def encrypt(plaintext: str) -> str:
    """AES-256-GCM encrypt. Returns base64(nonce ‖ ciphertext+tag)."""
    try:
        key = _get_key()
        nonce = os.urandom(_NONCE_SIZE)
        ciphertext_with_tag = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext_with_tag).decode("utf-8")
    except EncryptionError:
        raise
    except Exception as exc:
        raise EncryptionError(f"Encryption failed: {exc}")


def decrypt(ciphertext_b64: str) -> str:
    """AES-256-GCM decrypt. Returns original plaintext string."""
    try:
        key = _get_key()
        raw = base64.b64decode(ciphertext_b64)
        nonce, ciphertext_with_tag = raw[:_NONCE_SIZE], raw[_NONCE_SIZE:]
        plaintext = AESGCM(key).decrypt(nonce, ciphertext_with_tag, None)
        return plaintext.decode("utf-8")
    except EncryptionError:
        raise
    except Exception as exc:
        raise EncryptionError(f"Decryption failed: {exc}")
