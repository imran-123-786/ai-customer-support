"""
Security utilities: secure password hashing, verification, and role-based permissions.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-HMAC-SHA256 with 200,000 iterations."""
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200000)
    return "pbkdf2_sha256$200000$" + base64.b64encode(salt).decode("utf-8") + "$" + base64.b64encode(key).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hashed string using constant-time comparison."""
    try:
        scheme, iterations, salt_b64, key_b64 = hashed_password.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        expected_key = base64.b64decode(key_b64.encode("utf-8"))
        calc_key = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, int(iterations))
        return hmac.compare_digest(calc_key, expected_key)
    except Exception:
        return False
