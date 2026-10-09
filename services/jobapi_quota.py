"""Control local de cuota para no consumir la API accidentalmente."""

import json
import os
from datetime import datetime
from pathlib import Path


STATE_FILE = Path(os.getenv("JOBAPI_USAGE_FILE", "jobapi_usage.json"))


def _read() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def estado() -> tuple[int, int]:
    month = datetime.now().strftime("%Y-%m")
    data = _read()
    used = int(data.get(month, 0)) if data.get(month) is not None else 0
    limit = int(os.getenv("JOBAPI_MONTHLY_LIMIT", "200"))
    return used, limit


def puede_consultar() -> bool:
    used, limit = estado()
    return used < limit


def registrar_consulta() -> None:
    month = datetime.now().strftime("%Y-%m")
    data = _read()
    data[month] = int(data.get(month, 0)) + 1
    STATE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
