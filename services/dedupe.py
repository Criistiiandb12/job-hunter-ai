"""Claves de deduplicación independientes de la fuente."""

import hashlib
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _normalizar(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value).strip().lower()


def _url_sin_tracking(url: str | None) -> str:
    if not url:
        return ""
    try:
        partes = urlsplit(url.strip())
        parametros = [
            (key, value)
            for key, value in parse_qsl(partes.query, keep_blank_values=True)
            if not key.lower().startswith(("utm_", "ref", "src"))
        ]
        return urlunsplit((partes.scheme.lower(), partes.netloc.lower(), partes.path.rstrip("/"), urlencode(parametros), ""))
    except ValueError:
        return _normalizar(url)


def clave_oferta(job) -> str:
    """Identifica una oferta igual aunque provenga de otra fuente."""
    base = "|".join((_normalizar(job.title), _normalizar(job.company), _normalizar(job.location)))
    if not base.strip("|"):
        base = _url_sin_tracking(job.url)
    return hashlib.sha256(base.encode("utf-8")).hexdigest()
