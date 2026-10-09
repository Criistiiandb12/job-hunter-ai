import json
import os

from dotenv import load_dotenv

from app.database import contar_envios_hoy, marcar_enviada, obtener_ofertas_para_enviar
from services.message_formatter import crear_mensaje as crear_mensaje_web
from services.telegram import enviar_mensaje

load_dotenv()

CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID"))
LIMITE_DIARIO_TELEGRAM = 10


def crear_mensaje(oferta):
    job_id, title, source, url, match_score, summary, strengths, missing, reason = oferta
    strengths = json.loads(strengths or "[]")
    missing = json.loads(missing or "[]")
    fortalezas = "\n".join(f"• {item}" for item in strengths)
    faltantes = "\n".join(f"• {item}" for item in missing)
    return f"""🤖 NUEVA OFERTA — {match_score}% MATCH

💼 {title}

📝 RESUMEN

{summary}

✅ COINCIDE

{fortalezas}

⚠️ FALTANTES

{faltantes}

💡 ¿POR QUÉ ENCAJA?

{reason}

🔎 Fuente: {source}

🔗 Ver oferta:
{url}""".strip()


async def enviar_ofertas():
    enviados_hoy = contar_envios_hoy()
    disponibles = max(LIMITE_DIARIO_TELEGRAM - enviados_hoy, 0)

    if disponibles == 0:
        print(f"Límite diario de Telegram agotado: {enviados_hoy}/{LIMITE_DIARIO_TELEGRAM}")
        return {"notificadas": 0, "enviadas_hoy": enviados_hoy, "disponibles": 0}

    ofertas = obtener_ofertas_para_enviar(min_match=70, limit=disponibles)
    print(f"Ofertas con match >= 70: {len(ofertas)} | Disponibles hoy: {disponibles}")
    notificadas = 0

    for oferta in ofertas:
        job_id, title, *_ = oferta
        print(f"Enviando: {title}")
        try:
            await enviar_mensaje(chat_id=CHAT_ID, mensaje=crear_mensaje_web(oferta))
            marcar_enviada(job_id)
            notificadas += 1
            print("Enviada y marcada como sent.")
        except Exception as error:
            print(f"Error enviando {title}: {type(error).__name__}: {error!r}")

    return {
        "notificadas": notificadas,
        "enviadas_hoy": enviados_hoy + notificadas,
        "disponibles": disponibles - notificadas,
    }


if __name__ == "__main__":
    import asyncio

    asyncio.run(enviar_ofertas())
