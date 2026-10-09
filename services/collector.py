"""Recolecta ofertas, las filtra localmente y las deja en la cola de IA."""

import asyncio
import inspect
import os
import unicodedata

from app.database import guardar_oferta
from config.profile import PROFILE
from services.jobapi_quota import estado, puede_consultar, registrar_consulta
from services.dedupe import clave_oferta
from sources.getonbrd import buscar_ofertas, convertir_oferta
from sources.jobapirapi import (
    buscar_ofertas as buscar_ofertas_jobapi,
    convertir_oferta as convertir_oferta_jobapi,
    extraer_ofertas as extraer_ofertas_jobapi,
    obtener_detalle as obtener_detalle_jobapi,
    obtener_salario_estimado as obtener_salario_jobapi,
)

MIN_FILTER_SCORE = 35
NIVELES_EXCLUIDOS = ("senior", "mid", "lead", "principal", "staff", "director", "manager", "architect")
NIVELES_COMPATIBLES = ("junior", "entry", "trainee", "intern", "practicante", "aprendiz")


def normalizar(texto) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).lower().strip()


def detectar_nivel_excluido(job):
    titulo = normalizar(job.title)
    return next((nivel for nivel in NIVELES_EXCLUIDOS if nivel in titulo), None)


def detectar_nivel_compatible(job):
    titulo = normalizar(job.title)
    return next((nivel for nivel in NIVELES_COMPATIBLES if nivel in titulo), None)


def evaluar_cargo(job):
    titulo = normalizar(job.title)
    roles = [role for role in PROFILE.get("preferred_roles", []) if normalizar(role) in titulo]
    if roles:
        return 40, roles
    patrones = ("developer", "desarrollador", "programador", "software engineer", "software developer", "web developer", "backend", "back-end", "frontend", "front-end", "full stack", "full-stack")
    encontrados = [patron for patron in patrones if patron in titulo]
    return (30, encontrados) if encontrados else (0, [])


def evaluar_skills(job):
    texto = normalizar(f"{job.title} {job.description}")
    encontradas = [skill for skill in PROFILE.get("skills", []) if normalizar(skill) in texto]
    puntos = 30 if len(encontradas) >= 5 else 20 if len(encontradas) >= 3 else 10 if encontradas else 0
    return puntos, encontradas


def evaluar_ubicacion(job):
    location = normalizar(job.location)
    colombia = any(lugar in location for lugar in ("colombia", "medellin", "bogota", "bogota d.c", "cali", "barranquilla"))
    if colombia:
        return 15, "Colombia"
    if job.remote:
        return 15, "Remoto"
    for lugar in PROFILE.get("preferred_locations", []):
        if normalizar(lugar) in location:
            return 15, lugar
    return 0, None


def evaluar_oferta(job):
    excluido = detectar_nivel_excluido(job)
    if excluido:
        return {"pasa": False, "score": 0, "motivo": f"Nivel no compatible: {excluido}", "roles": [], "skills": []}
    cargo, roles = evaluar_cargo(job)
    skills, skills_encontradas = evaluar_skills(job)
    ubicacion, ubicacion_nombre = evaluar_ubicacion(job)
    nivel = detectar_nivel_compatible(job)
    puntos_nivel = 20 if nivel else 0
    score = cargo + skills + ubicacion + puntos_nivel
    if cargo == 0:
        motivo = "Cargo no relacionado"
        pasa = False
    elif skills == 0 and not nivel:
        motivo = "Cargo relacionado pero sin tecnologías compatibles ni nivel Junior"
        pasa = False
    else:
        pasa = score >= MIN_FILTER_SCORE
        motivo = f"Score {score} (cargo={cargo}, skills={skills}, ubicación={ubicacion}, nivel={puntos_nivel})"
    return {"pasa": pasa, "score": score, "motivo": motivo, "roles": roles, "skills": skills_encontradas, "ubicacion": ubicacion_nombre}


async def _fuentes(query: str, country_code: str, incluir_jobapi: bool):
    respuesta = await buscar_ofertas(query=query, country_code=country_code)
    fuentes = [("Get on Board", respuesta.get("data", []), convertir_oferta)]
    if incluir_jobapi:
        usadas, limite = estado()
        if not puede_consultar():
            print(f"Job API omitida: cuota mensual agotada ({usadas}/{limite}).")
            return fuentes
        try:
            respuesta_api = await buscar_ofertas_jobapi(
                query=os.getenv("JOBAPI_QUERY", "developer jobs in Colombia"),
                location=os.getenv("JOBAPI_LOCATION", "Colombia"),
            )
            registrar_consulta()
            ofertas_jobapi = extraer_ofertas_jobapi(respuesta_api)
            print(f"📡 Job API/JSearch: {len(ofertas_jobapi)} ofertas recibidas")
            fuentes.append(("Job API", ofertas_jobapi, convertir_oferta_jobapi))
        except Exception as error:
            print(
                "Job API no disponible; se conserva Get on Board: "
                f"{type(error).__name__}: {error!r}"
            )
    return fuentes


async def _llamada_jobapi(llamada):
    """Ejecuta una llamada adicional solo si queda cuota y la registra."""
    usadas, limite = estado()
    if not puede_consultar():
        print(f"Job API: cuota agotada durante enriquecimiento ({usadas}/{limite}).")
        return None
    try:
        respuesta = await llamada()
        registrar_consulta()
        return respuesta
    except Exception as error:
        print(f"Job API: error durante enriquecimiento ({type(error).__name__}): {error!r}")
        return None


async def _enriquecer_jobapi(candidatas_ordenadas):
    """Detalle y salario solo para las mejores candidatas de JSearch."""
    limite = int(os.getenv("JOBAPI_ENRICH_LIMIT", "3"))
    enriquecidas = 0
    resultado = []

    for score, job in candidatas_ordenadas:
        if job.source == "Job API" and enriquecidas < limite:
            raw_id = job.source_id or job.id.removeprefix("jobapi-")
            detalle = await _llamada_jobapi(lambda: obtener_detalle_jobapi(raw_id))
            if detalle:
                detalles = detalle.get("data") or []
                if isinstance(detalles, list) and detalles:
                    job = convertir_oferta_jobapi(detalles[0])

            if job.salary_min is None and job.salary_max is None:
                salario = await _llamada_jobapi(
                    lambda: obtener_salario_jobapi(job.title, job.location)
                )
                datos_salario = (salario or {}).get("data") or []
                if isinstance(datos_salario, list) and datos_salario:
                    job.salary_min = datos_salario[0].get("min_salary")
                    job.salary_max = datos_salario[0].get("max_salary")

            enriquecidas += 1
            print(f"📌 Job API enriquecida: {job.title} → Score {score}")

        resultado.append((score, job))

    return resultado


async def recolectar_ofertas(query: str = "python", country_code: str = "CO", incluir_jobapi: bool = True):
    """Consulta cada fuente una vez, filtra sin IA y guarda solo candidatas."""
    print("\n🔎 Buscando nuevas ofertas...")
    fuentes = await _fuentes(query, country_code, incluir_jobapi)
    total = sum(len(ofertas) for _, ofertas, _ in fuentes)
    print(f"📋 Ofertas encontradas: {total}")
    candidatas = descartadas = nuevas = 0
    candidatas_ordenadas = []
    conteos = {
        fuente: {"encontradas": len(ofertas), "candidatas": 0, "descartadas": 0, "guardadas": 0}
        for fuente, ofertas, _ in fuentes
    }

    for fuente, ofertas, convertir in fuentes:
        for oferta in ofertas:
            try:
                job = convertir(oferta)
                if inspect.isawaitable(job):
                    job = await job
                resultado = evaluar_oferta(job)
                if not resultado["pasa"]:
                    descartadas += 1
                    conteos[fuente]["descartadas"] += 1
                    print(f"🚫 Descartada: {job.title} → {resultado['motivo']}")
                    continue
                candidatas += 1
                conteos[fuente]["candidatas"] += 1
                candidatas_ordenadas.append((resultado["score"], job))
                print(f"🤖 Candidata: {job.title} → {resultado['motivo']}")
            except Exception as error:
                print(f"Error procesando oferta de {fuente}: {error}")

    candidatas_ordenadas = await _enriquecer_jobapi(
        sorted(candidatas_ordenadas, key=lambda item: item[0], reverse=True)
    )

    for score, job in candidatas_ordenadas:
        try:
            inserted = guardar_oferta(
                job_id=job.id, title=job.title, company=job.company, location=job.location,
                description=job.description, source=job.source, url=job.url,
                salary_min=job.salary_min, salary_max=job.salary_max, remote=job.remote,
                filter_score=score, dedupe_key=clave_oferta(job)
            )
            if inserted:
                nuevas += 1
                conteos[job.source]["guardadas"] += 1
            else:
                print(f"♻️ Duplicada omitida: {job.title}")
        except Exception as error:
            print(f"Error guardando {job.title}: {error}")

    print("\n" + "=" * 60)
    print(f"📋 Ofertas encontradas: {total}")
    print(f"🤖 Candidatas para IA: {candidatas}")
    print(f"🚫 Descartadas: {descartadas}")
    print(f"📥 Guardadas en PostgreSQL: {nuevas}")
    print("\n📊 Desglose por fuente:")
    for fuente, datos in conteos.items():
        print(
            f"  {fuente}: encontradas={datos['encontradas']}, "
            f"candidatas={datos['candidatas']}, "
            f"descartadas={datos['descartadas']}, "
            f"guardadas={datos['guardadas']}"
        )
    print("=" * 60)
    return {
        "encontradas": total,
        "candidatas": candidatas,
        "descartadas": descartadas,
        "guardadas": nuevas,
        "por_fuente": conteos,
    }


async def main():
    await recolectar_ofertas()


if __name__ == "__main__":
    asyncio.run(main())
