import httpx


BASE_URL = "https://www.getonbrd.com/api/v0"

empresas_cache = {}


async def obtener_empresa(company_id: int):

    # Revisar si ya tenemos la empresa en memoria
    if company_id in empresas_cache:
        return empresas_cache[company_id]

    url = f"{BASE_URL}/companies/{company_id}"

    async with httpx.AsyncClient() as client:

        response = await client.get(
            url,
            timeout=30
        )

        response.raise_for_status()

        respuesta = response.json()

        nombre = respuesta["data"]["attributes"]["name"]

        # Guardar en caché
        empresas_cache[company_id] = nombre

        return nombre