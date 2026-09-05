import os
import base64
import hashlib
from cryptography.fernet import Fernet


def _get_key():
    raw = os.getenv("SECRET_KEY", "dev-secret")
    return base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    f = Fernet(_get_key())
    return f.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    f = Fernet(_get_key())
    return f.decrypt(ciphertext.encode()).decode()
