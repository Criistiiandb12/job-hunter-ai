"""Autenticación mínima para el panel administrativo."""

import base64
import hashlib
import hmac
import json
import os
import time

from dotenv import load_dotenv

load_dotenv()


def _secret() -> bytes:
    secret = os.getenv("ADMIN_SECRET")
    if not secret:
        raise RuntimeError("Falta ADMIN_SECRET en el archivo .env")
    return secret.encode("utf-8")


def validar_credenciales(username: str, password: str) -> bool:
    expected_user = os.getenv("ADMIN_USERNAME", "admin")
    expected_password = os.getenv("ADMIN_PASSWORD")
    if not expected_password:
        raise RuntimeError("Falta ADMIN_PASSWORD en el archivo .env")
    return hmac.compare_digest(username, expected_user) and hmac.compare_digest(password, expected_password)


def crear_token(username: str, ttl_seconds: int = 28800) -> str:
    payload = {"sub": username, "exp": int(time.time()) + ttl_seconds}
    raw = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
    return f"{raw}.{signature}"


def validar_token(token: str) -> bool:
    try:
        raw, signature = token.split(".", 1)
        expected = hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        padding = "=" * (-len(raw) % 4)
        payload = json.loads(base64.urlsafe_b64decode(raw + padding))
        return bool(payload.get("sub")) and int(payload.get("exp", 0)) > int(time.time())
    except (ValueError, TypeError, json.JSONDecodeError, KeyError):
        return False
