"""Adaptador de empleos basado en RapidAPI.

La búsqueda devuelve lo necesario para puntuar. No se solicitan detalles por
oferta: cada ejecución consume como máximo una petición de la API.
"""

import html
import hashlib
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv

from app.models import Job

load_dotenv()

BASE_URL = os.getenv("JOBAPI_BASE_URL", "https://jsearch.p.rapidapi.com").rstrip("/")
SEARCH_PATH = os.getenv("JOBAPI_SEARCH_PATH", "/search-v2")
RAPIDAPI_HOST = os.getenv("JOBAPI_RAPIDAPI_HOST", "jsearch.p.rapidapi.com")


def _headers() -> dict[str, str]:
    api_key = os.getenv("RAPIDAPI_KEY")
    if not api_key:
        raise RuntimeError("No se encontró RAPIDAPI_KEY en el archivo .env")
    return {"accept": "application/json", "x-rapidapi-host": RAPIDAPI_HOST, "x-rapidapi-key": api_key}


async def buscar_ofertas(query: str = "developer jobs in Colombia", location: str = "Colombia", *, timeout: float = 30) -> dict[str, Any]:
    """Hace una sola petición de búsqueda y devuelve el JSON crudo."""
    params = {
        "query": query,
        "num_pages": 1,
        "country": os.getenv("JOBAPI_COUNTRY", "co"),
        "date_posted": os.getenv("JOBAPI_DATE_POSTED", "all"),
    }
    if location:
        params["location"] = location
    if os.getenv("JOBAPI_LANGUAGE"):
        params["language"] = os.getenv("JOBAPI_LANGUAGE")
    if os.getenv("JOBAPI_REQUIREMENTS"):
        params["job_requirements"] = os.getenv("JOBAPI_REQUIREMENTS")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}{SEARCH_PATH}",
            headers=_headers(),
            params=params,
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("La API de empleos no devolvió un objeto JSON")
    if payload.get("status") not in (None, "OK"):
        raise RuntimeError(f"JSearch devolvió estado {payload.get('status')}")
    return payload


async def obtener_detalle(job_id: str, *, timeout: float = 30) -> dict[str, Any]:
    """Obtiene el detalle documentado de una oferta concreta."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/job-details",
            headers=_headers(),
            params={"job_id": job_id, "country": os.getenv("JOBAPI_COUNTRY", "co")},
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    if payload.get("status") not in (None, "OK"):
        raise RuntimeError(f"JSearch devolviÃ³ estado {payload.get('status')}")
    return payload


async def obtener_salario_estimado(job_title: str, location: str = "Colombia", *, timeout: float = 30) -> dict[str, Any]:
    """Obtiene el salario estimado documentado para un cargo."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/estimated-salary",
            headers=_headers(),
            params={
                "job_title": job_title,
                "location": location,
                "location_type": os.getenv("JOBAPI_SALARY_LOCATION_TYPE", "ANY"),
                "years_of_experience": os.getenv("JOBAPI_YEARS_OF_EXPERIENCE", "ALL"),
            },
            timeout=timeout,
        )
        response.raise_for_status()
        payload = response.json()
    if payload.get("status") not in (None, "OK"):
        raise RuntimeError(f"JSearch devolviÃ³ estado {payload.get('status')}")
    return payload


def extraer_ofertas(respuesta: dict[str, Any]) -> list[dict[str, Any]]:
    data = respuesta.get("data")
    if isinstance(data, dict) and isinstance(data.get("jobs"), list):
        return data["jobs"]
    for key in ("data", "results", "jobs", "job_results"):
        value = respuesta.get(key)
        if isinstance(value, list):
            return value
    return []


def limpiar_html(texto: Any) -> str:
    if not texto:
        return ""
    texto = re.sub(r"<[^>]+>", " ", str(texto))
    return re.sub(r"\s+", " ", html.unescape(texto)).strip()


def _first(*values: Any) -> Any:
    return next((value for value in values if value not in (None, "")), None)


def _number(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    if value is None:
        return None
    match = re.search(r"\d[\d,.]*", str(value))
    if not match:
        return None
    try:
        return int(float(match.group().replace(",", "")))
    except ValueError:
        return None


def convertir_oferta(oferta: dict[str, Any]) -> Job:
    """Convierte respuestas comunes del proveedor al modelo interno Job."""
    company = oferta.get("company")
    if isinstance(company, dict):
        company = _first(company.get("name"), company.get("title"))
    salary = oferta.get("salary") or {}
    if not isinstance(salary, dict):
        salary = {}
    location = _first(oferta.get("job_location"), oferta.get("location"), oferta.get("locality"), oferta.get("city"), "No especificada")
    description = limpiar_html(_first(oferta.get("description"), oferta.get("job_description"), oferta.get("snippet"), ""))
    remote_value = oferta.get("job_is_remote", oferta.get("remote", oferta.get("is_remote", False)))
    remote_text = f"{location} {oferta.get('job_title', '')} {description}".lower()
    remote = bool(remote_value) or any(marker in remote_text for marker in ("remote", "remoto", "teletrabajo"))
    external_id = _first(oferta.get("id"), oferta.get("job_id"), oferta.get("uid"))
    url = _first(oferta.get("job_apply_link"), oferta.get("url"), oferta.get("link"), oferta.get("job_url"), oferta.get("indeed_final_url"), "")
    title = _first(oferta.get("job_title"), oferta.get("title"), "Sin título")
    if external_id:
        external_id_text = str(external_id)
        # JSearch devuelve IDs codificados que pueden superar ampliamente
        # VARCHAR(255). Un hash mantiene un identificador estable y corto.
        if len(external_id_text) > 200:
            stable_id = hashlib.sha256(external_id_text.encode("utf-8")).hexdigest()
        else:
            stable_id = external_id_text
    else:
        stable_id = hashlib.sha256(f"{title}|{url}".encode("utf-8")).hexdigest()[:24]
    return Job(
        id=f"jobapi-{stable_id}",
        title=title,
        company=company or _first(oferta.get("employer_name"), oferta.get("company_name"), "No especificada"),
        location=str(location),
        description=description,
        url=str(url),
        salary_min=_number(_first(salary.get("min"), oferta.get("job_min_salary"), oferta.get("salary_min"))),
        salary_max=_number(_first(salary.get("max"), oferta.get("job_max_salary"), oferta.get("salary_max"))),
        remote=remote,
        source="Job API",
        source_id=str(external_id) if external_id is not None else None,
    )


async def main() -> None:
    """Prueba manual de la fuente: una búsqueda, sin llamadas de detalle."""
    from services.jobapi_quota import estado, puede_consultar, registrar_consulta

    usadas, limite = estado()
    print("\nBuscando ofertas en JSearch...")
    print(f"Cuota local: {usadas}/{limite} consultas usadas este mes")

    if not puede_consultar():
        print("Cuota mensual agotada; no se hará ninguna petición.")
        return

    try:
        respuesta = await buscar_ofertas(
            query=os.getenv("JOBAPI_QUERY", "developer jobs in Colombia"),
            location=os.getenv("JOBAPI_LOCATION", "Colombia"),
        )
        registrar_consulta()
    except Exception as error:
        print(f"Error consultando JSearch: {error}")
        return

    ofertas = extraer_ofertas(respuesta)
    print(f"Ofertas encontradas: {len(ofertas)}")

    for oferta in ofertas[:5]:
        job = convertir_oferta(oferta)
        print("\n" + "=" * 60)
        print(f"Cargo: {job.title}")
        print(f"Empresa: {job.company}")
        print(f"Ubicación: {job.location}")
        print(f"Remoto: {job.remote}")
        print(f"Salario: {job.salary_min} - {job.salary_max}")
        print(f"URL: {job.url}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
