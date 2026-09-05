"""JWT 与密码哈希（各服务共享同一套签名密钥与算法）。"""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

_password_hash = PasswordHash((BcryptHasher(),))


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash_stored: str) -> bool:
    return _password_hash.verify(password, password_hash_stored)


def _create_token(subject: str, token_type: str, expires_delta: timedelta, secret: str) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def create_access_token(user_id: int, secret: str, minutes: int = 30) -> str:
    return _create_token(str(user_id), "access", timedelta(minutes=minutes), secret)


def create_refresh_token(user_id: int, secret: str, days: int = 7) -> str:
    return _create_token(str(user_id), "refresh", timedelta(days=days), secret)


def decode_token(token: str, secret: str, expected_type: str = "access") -> int:
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected {expected_type} token")
    return int(payload["sub"])
