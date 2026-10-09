import asyncio
import httpx

from app.models import Job
from sources.company import obtener_empresa


URL = "https://www.getonbrd.com/api/v0/search/jobs"


async def buscar_ofertas(
    query: str = "python",
    country_code: str = "CO"
):

    params = {
        "query": query,
        "country_code": country_code
    }

    async with httpx.AsyncClient() as client:

        response = await client.get(
            URL,
            params=params,
            timeout=30
        )

        response.raise_for_status()

        return response.json()


async def convertir_oferta(oferta: dict) -> Job:

    attributes = oferta["attributes"]

    salario_min = attributes.get("min_salary")
    salario_max = attributes.get("max_salary")

    company_data = attributes.get("company", {}).get("data")

    if company_data:

        company_id = company_data["id"]

        try:
            company_name = await obtener_empresa(company_id)
        except Exception:
            company_name = "No especificada"

    else:
        company_name = "No especificada"

    if attributes.get("remote"):

        location = "Remoto"

    elif attributes.get("countries"):

        location = ", ".join(attributes["countries"])

    else:

        location = "No especificada"

    return Job(
        id=oferta["id"],
        title=attributes["title"],
        company=company_name,
        location=location,
        description=attributes.get("description", ""),
        url=oferta["links"]["public_url"],
        salary_min=salario_min,
        salary_max=salario_max,
        remote=attributes.get("remote", False),
        source="Get on Board"
    )


async def main():

    respuesta = await buscar_ofertas()

    ofertas = respuesta.get("data", [])

    print(f"\nOfertas encontradas: {len(ofertas)}\n")

    for oferta in ofertas[:5]:

        job = await convertir_oferta(oferta)

        print("=" * 60)
        print(f"Cargo: {job.title}")
        print(f"Empresa: {job.company}")
        print(f"Ubicación: {job.location}")
        print(f"Remoto: {job.remote}")
        print(f"Salario: {job.salary_min} - {job.salary_max}")
        print(f"URL: {job.url}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())