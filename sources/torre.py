import httpx


TORRE_URL = "https://torre.co/api/sop/jobs"


async def buscar_ofertas():
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            TORRE_URL,
            timeout=30
        )

        print("Status:", response.status_code)
        print("URL final:", response.url)

        response.raise_for_status()

        return response.json()


async def main():
    ofertas = await buscar_ofertas()

    print(type(ofertas))
    print(ofertas)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())