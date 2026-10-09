"""Ejecuta el pipeline completo y registra cada ejecución en PostgreSQL."""

import asyncio

from app.database import actualizar_progreso, crear_ejecucion, finalizar_ejecucion
from services.analyzer import analizar_pendientes
from services.collector import recolectar_ofertas
from services.notifier import enviar_ofertas


async def main():
    run_id = crear_ejecucion()
    coleccion = {}
    analisis = {}
    notificacion = {}

    print("\n" + "=" * 60)
    print("JOB HUNTER IA")
    print(f"Ejecución #{run_id}")
    print("=" * 60)

    try:
        actualizar_progreso(run_id, "collecting", "Buscando ofertas en Get on Board y Job API...")
        print("\nFASE 1 — RECOLECTOR")
        coleccion = await recolectar_ofertas()
        actualizar_progreso(run_id, "collecting", f"Recolección terminada: {coleccion.get('encontradas', 0)} ofertas encontradas.", found_count=coleccion.get("encontradas", 0), filtered_count=coleccion.get("candidatas", 0))

        print("\nFASE 2 — ANALIZADOR")
        actualizar_progreso(run_id, "analyzing", "Analizando las ofertas compatibles con IA...")
        analisis = await analizar_pendientes(limit=10, intervalo=30) or {}
        actualizar_progreso(run_id, "analyzing", f"Análisis terminado: {analisis.get('analizadas', 0)} ofertas evaluadas.", analyzed_count=analisis.get("analizadas", 0))

        print("\nFASE 3 — NOTIFICADOR")
        actualizar_progreso(run_id, "notifying", "Enviando las mejores ofertas a Telegram...")
        notificacion = await enviar_ofertas() or {}
        actualizar_progreso(run_id, "notifying", f"Telegram: {notificacion.get('notificadas', 0)} ofertas enviadas.", notified_count=notificacion.get("notificadas", 0))

        finalizar_ejecucion(
            run_id,
            "completed",
            found_count=coleccion.get("encontradas", 0),
            filtered_count=coleccion.get("candidatas", 0),
            analyzed_count=analisis.get("analizadas", 0),
            notified_count=notificacion.get("notificadas", 0),
        )
        print("\nPIPELINE FINALIZADO CORRECTAMENTE")
    except Exception as error:
        finalizar_ejecucion(
            run_id,
            "error",
            found_count=coleccion.get("encontradas", 0),
            filtered_count=coleccion.get("candidatas", 0),
            analyzed_count=analisis.get("analizadas", 0),
            notified_count=notificacion.get("notificadas", 0),
            error_message=f"{type(error).__name__}: {error}",
        )
        print(f"PIPELINE FINALIZADO CON ERROR: {type(error).__name__}: {error}")
        raise

    return {
        "run_id": run_id,
        "collector": coleccion,
        "analyzer": analisis,
        "notifier": notificacion,
    }


if __name__ == "__main__":
    asyncio.run(main())
