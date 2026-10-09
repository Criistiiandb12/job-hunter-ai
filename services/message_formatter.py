"""Formato único para las recomendaciones que llegan a Telegram y a la web."""

import json


def crear_mensaje(oferta) -> str:
    (
        _job_id,
        title,
        source,
        url,
        match_score,
        summary,
        strengths,
        missing,
        reason,
    ) = oferta
    fortalezas = _lista(strengths)
    faltantes = _lista(missing)
    return f"""🤖 NUEVA OFERTA — {match_score}% MATCH

💼 {title}

📝 RESUMEN

{summary or "Sin resumen disponible."}

✅ COINCIDE

{fortalezas or "• No especificado"}

⚠️ FALTANTES

{faltantes or "• No especificado"}

💡 ¿POR QUÉ ENCAJA?

{reason or "Sin explicación disponible."}

🔎 Fuente: {source}

🔗 Ver oferta:
{url}""".strip()


def _lista(value) -> str:
    if isinstance(value, list):
        items = value
    else:
        try:
            items = json.loads(str(value or "[]"))
        except (TypeError, json.JSONDecodeError):
            items = []
    return "\n".join(f"• {item}" for item in items)
