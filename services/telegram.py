import os

from dotenv import load_dotenv
from telegram import Bot

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def enviar_mensaje(chat_id: int, mensaje: str):
    bot = Bot(token=TELEGRAM_BOT_TOKEN)

    await bot.send_message(
        chat_id=chat_id,
        text=mensaje,
        disable_web_page_preview=False
    )


def formatear_oferta(job):
    salario = "No especificado"

    if job.salary_min is not None and job.salary_max is not None:
        salario = f"{job.salary_min} - {job.salary_max}"
    elif job.salary_min is not None:
        salario = f"Desde {job.salary_min}"
    elif job.salary_max is not None:
        salario = f"Hasta {job.salary_max}"

    modalidad = "Remoto" if job.remote else job.location

    mensaje = f"""
🤖 NUEVA OFERTA

💼 {job.title}

🏢 Empresa: {job.company}

📍 Ubicación: {modalidad}

💰 Salario: {salario}

🔎 Fuente: {job.source}

🔗 Ver oferta:
{job.url}
"""

def formatear_oferta_ia(job, analisis):
    
    salario = "No especificado"

    if job.salary_min is not None and job.salary_max is not None:
        salario = f"{job.salary_min} - {job.salary_max}"
    elif job.salary_min is not None:
        salario = f"Desde {job.salary_min}"
    elif job.salary_max is not None:
        salario = f"Hasta {job.salary_max}"

    modalidad = "Remoto" if job.remote else job.location

    fortalezas = "\n".join(
        f"• {item}"
        for item in analisis["strengths"]
    )

    faltantes = "\n".join(
        f"• {item}"
        for item in analisis["missing"]
    )

    mensaje = f"""
🤖 NUEVA OFERTA — {analisis["match"]}% MATCH

💼 {job.title}

🏢 Empresa: {job.company}

📍 Ubicación: {modalidad}

💰 Salario: {salario}

📝 RESUMEN

{analisis["summary"]}

✅ COINCIDE

{fortalezas}

⚠️ FALTANTES

{faltantes}

💡 ¿POR QUÉ ENCAJA?

{analisis["reason"]}

🔎 Fuente: {job.source}

🔗 Ver oferta:
{job.url}
"""

    return mensaje.strip()

