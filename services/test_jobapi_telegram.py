"""Envía una sola oferta Job API como prueba controlada del flujo completo."""

import asyncio
import os

from dotenv import load_dotenv

from app.database import (
    devolver_a_pendiente,
    guardar_analisis,
    marcar_analizando,
    marcar_enviada,
    obtener_oferta_pendiente_por_fuente,
)
from app.models import Job
from services.ai import analizar_oferta
from services.telegram import enviar_mensaje, formatear_oferta_ia

load_dotenv()


async def main():
    oferta = obtener_oferta_pendiente_por_fuente("Job API")
    if not oferta:
        print("No hay ofertas Job API pendientes para probar.")
        return

    (
        job_id, title, company, location, description,
        source, url, salary_min, salary_max, remote, filter_score,
    ) = oferta

    job = Job(
        id=job_id,
        title=title,
        company=company,
        location=location,
        description=description or "",
        url=url,
        salary_min=salary_min,
        salary_max=salary_max,
        remote=remote,
        source=source,
    )

    print(f"Probando una oferta Job API: {job.title} (score local: {filter_score})")
    marcar_analizando(job_id)

    try:
        analisis = await analizar_oferta(job)
        if analisis is None:
            devolver_a_pendiente(job_id)
            print("La IA no devolvió un análisis; la oferta volvió a pending.")
            return

        guardar_analisis(
            job_id=job_id,
            match_score=analisis["match"],
            summary=analisis["summary"],
            strengths=analisis["strengths"],
            missing=analisis["missing"],
            reason=analisis["reason"],
        )

        print(f"Match IA: {analisis['match']}%")
        forzar_prueba = os.getenv("JOBAPI_TEST_FORCE_SEND") == "1"
        if analisis["match"] < 70 and not forzar_prueba:
            print("No se envía: no alcanzó el umbral de 70%.")
            return

        mensaje = formatear_oferta_ia(job, analisis)
        if forzar_prueba:
            mensaje = "🧪 PRUEBA JOB API\n\n" + mensaje

        await enviar_mensaje(
            chat_id=int(os.getenv("TELEGRAM_CHAT_ID")),
            mensaje=mensaje,
        )
        marcar_enviada(job_id)
        print("Oferta Job API enviada a Telegram y marcada como sent.")
    except Exception:
        devolver_a_pendiente(job_id)
        raise


if __name__ == "__main__":
    asyncio.run(main())
