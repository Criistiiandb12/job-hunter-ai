import os
import json

import psycopg
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def obtener_conexion():

    return psycopg.connect(DATABASE_URL)


# =========================================================
# OFERTAS
# =========================================================

def oferta_ya_enviada(job_id: str) -> bool:

    with obtener_conexion() as conexion:

        with conexion.cursor() as cursor:

            cursor.execute(
                """
                SELECT 1
                FROM jobs_seen
                WHERE job_id = %s
                AND status = 'sent'
                """,
                (job_id,)
            )

            resultado = cursor.fetchone()

            return resultado is not None


def guardar_oferta(
    job_id: str,
    title: str,
    company: str,
    location: str,
    description: str,
    source: str,
    url: str,
    salary_min: int | None,
    salary_max: int | None,
    remote: bool,
    filter_score: int,
    dedupe_key: str | None = None
):

    with obtener_conexion() as conexion:

        with conexion.cursor() as cursor:

            cursor.execute(
                """
                INSERT INTO jobs_seen (
                    job_id,
                    title,
                    company,
                    location,
                    description,
                    source,
                    url,
                    salary_min,
                    salary_max,
                    remote,
                    filter_score,
                    dedupe_key,
                    status
                )

                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, 'pending'
                )

                ON CONFLICT
                DO NOTHING
                """,
                (
                    job_id,
                    title,
                    company,
                    location,
                    description,
                    source,
                    url,
                    salary_min,
                    salary_max,
                    remote,
                    filter_score,
                    dedupe_key
                )
            )
            inserted = cursor.rowcount > 0

        conexion.commit()
    return inserted


# =========================================================
# COLA DE ANÁLISIS
# =========================================================

def obtener_ofertas_pendientes(limit: int = 5):
    
    with obtener_conexion() as conexion:

        with conexion.cursor() as cursor:

            # Recuperar análisis interrumpidos.
            # Si llevan más de 15 minutos en "analyzing",
            # vuelven automáticamente a "pending".

            cursor.execute(
                """
                UPDATE jobs_seen
                SET
                    status = 'pending',
                    analyzing_at = NULL
                WHERE status = 'analyzing'
                AND analyzing_at < CURRENT_TIMESTAMP - INTERVAL '15 minutes'
                """
            )

            cursor.execute(
                """
                SELECT
                    job_id,
                    title,
                    company,
                    location,
                    description,
                    source,
                    url,
                    salary_min,
                    salary_max,
                    remote,
                    filter_score
                FROM jobs_seen
                WHERE status = 'pending'
                ORDER BY filter_score DESC NULLS LAST
                LIMIT %s
                """,
                (limit,)
            )

            return cursor.fetchall()


def obtener_oferta_pendiente_por_fuente(source: str):
    """Obtiene como máximo una oferta pendiente de una fuente concreta."""
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    job_id, title, company, location, description,
                    source, url, salary_min, salary_max, remote, filter_score
                FROM jobs_seen
                WHERE status = 'pending' AND source = %s
                ORDER BY filter_score DESC NULLS LAST
                LIMIT 1
                """,
                (source,),
            )
            return cursor.fetchone()


def marcar_analizando(job_id: str):
    
    with obtener_conexion() as conexion:

        with conexion.cursor() as cursor:

            cursor.execute(
                """
                UPDATE jobs_seen
                SET
                    status = 'analyzing',
                    analyzing_at = CURRENT_TIMESTAMP
                WHERE job_id = %s
                """,
                (job_id,)
            )

        conexion.commit()


def guardar_analisis(
    job_id: str,
    match_score: int,
    summary: str,
    strengths: list,
    missing: list,
    reason: str
):

    with obtener_conexion() as conexion:

        with conexion.cursor() as cursor:

            cursor.execute(
                """
                UPDATE jobs_seen

                SET
                    status = 'analyzed',
                    match_score = %s,
                    analyzing_at = NULL,
                    ai_summary = %s,
                    ai_strengths = %s,
                    ai_missing = %s,
                    ai_reason = %s,
                    analyzed_at = CURRENT_TIMESTAMP

                WHERE job_id = %s
                """,
                (
                    match_score,
                    summary,
                    json.dumps(strengths, ensure_ascii=False),
                    json.dumps(missing, ensure_ascii=False),
                    reason,
                    job_id
                )
            )

        conexion.commit()


def devolver_a_pendiente(job_id: str):

    with obtener_conexion() as conexion:

        with conexion.cursor() as cursor:

            cursor.execute(
                """
                UPDATE jobs_seen

                SET
                    status = 'pending',
                    analyzing_at = NULL

                WHERE job_id = %s
                """,
                (job_id,)
            )

        conexion.commit()


# =========================================================
# TELEGRAM
# =========================================================

def obtener_ofertas_para_enviar(min_match: int = 70, limit: int = 10):

    with obtener_conexion() as conexion:

        with conexion.cursor() as cursor:

            cursor.execute(
                """
                SELECT
                    job_id,
                    title,
                    source,
                    url,
                    match_score,
                    ai_summary,
                    ai_strengths,
                    ai_missing,
                    ai_reason

                FROM jobs_seen

                WHERE status = 'analyzed'
                AND match_score >= %s

                ORDER BY match_score DESC
                LIMIT %s
                """,
                (min_match, limit)
            )

            return cursor.fetchall()


def marcar_enviada(job_id: str):

    with obtener_conexion() as conexion:

        with conexion.cursor() as cursor:

            cursor.execute(
                """
                UPDATE jobs_seen

                SET
                    status = 'sent',
                    sent_at = CURRENT_TIMESTAMP

                WHERE job_id = %s
                """,
                (job_id,)
            )


        conexion.commit()

def contar_analisis_hoy(source: str) -> int:
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM jobs_seen
                WHERE source = %s
                AND analyzed_at >= CURRENT_DATE
                """,
                (source,)
            )

            resultado = cursor.fetchone()

            return resultado[0]


def contar_envios_hoy() -> int:
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM jobs_seen
                WHERE status = 'sent' AND sent_at >= CURRENT_DATE
                """
            )
            return cursor.fetchone()[0]


def crear_ejecucion() -> int:
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                "INSERT INTO pipeline_runs (status, current_step, phase_message) VALUES ('running', 'starting', 'Preparando pipeline...') RETURNING run_id"
            )
            run_id = cursor.fetchone()[0]
        conexion.commit()
    return run_id


def actualizar_progreso(run_id: int, current_step: str, phase_message: str, **counts) -> None:
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                UPDATE pipeline_runs
                SET current_step = %s, phase_message = %s,
                    found_count = COALESCE(%s, found_count),
                    filtered_count = COALESCE(%s, filtered_count),
                    analyzed_count = COALESCE(%s, analyzed_count),
                    notified_count = COALESCE(%s, notified_count),
                    updated_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                """,
                (
                    current_step,
                    phase_message,
                    counts.get("found_count"),
                    counts.get("filtered_count"),
                    counts.get("analyzed_count"),
                    counts.get("notified_count"),
                    run_id,
                ),
            )
        conexion.commit()


def finalizar_ejecucion(run_id: int, status: str, **counts) -> None:
    values = (
        status,
        counts.get("found_count", 0),
        counts.get("filtered_count", 0),
        counts.get("analyzed_count", 0),
        counts.get("notified_count", 0),
        counts.get("error_message"),
        "completed" if status == "completed" else "error",
        "Pipeline completado." if status == "completed" else "Pipeline finalizado con error.",
        run_id,
    )
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                UPDATE pipeline_runs
                SET ended_at = CURRENT_TIMESTAMP,
                    status = %s,
                    found_count = %s,
                    filtered_count = %s,
                    analyzed_count = %s,
                    notified_count = %s,
                    error_message = %s,
                    current_step = %s,
                    phase_message = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE run_id = %s
                """,
                values,
            )
        conexion.commit()


def obtener_ofertas_web(limit: int = 50):
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT job_id, title, company, location, description, source, url,
                       salary_min, salary_max, remote, filter_score,
                       match_score, status, analyzed_at, sent_at,
                       ai_summary, ai_strengths, ai_missing, ai_reason
                FROM jobs_seen
                WHERE status IN ('analyzed', 'sent')
                ORDER BY COALESCE(match_score, filter_score, 0) DESC, job_id
                LIMIT %s
                """,
                (limit,),
            )
            return cursor.fetchall()


def obtener_ejecuciones_web(limit: int = 20):
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT run_id, started_at, ended_at, status,
                       found_count, filtered_count, analyzed_count,
                       notified_count, error_message, current_step,
                       phase_message, updated_at
                FROM pipeline_runs
                ORDER BY started_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cursor.fetchall()


def obtener_estadisticas_web():
    with obtener_conexion() as conexion:
        with conexion.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE),
                    COUNT(*) FILTER (WHERE status IN ('analyzed', 'sent')),
                    COUNT(*) FILTER (WHERE status = 'sent' AND sent_at >= CURRENT_DATE),
                    COUNT(*) FILTER (WHERE source = 'Get on Board'),
                    COUNT(*) FILTER (WHERE source = 'Job API')
                FROM jobs_seen
                """
            )
            return cursor.fetchone()
