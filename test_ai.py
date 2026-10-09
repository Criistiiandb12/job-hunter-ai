import asyncio

from sources.getonbrd import buscar_ofertas, convertir_oferta
from services.ai import analizar_oferta


async def main():

    respuesta = await buscar_ofertas(
        query="python",
        country_code="CO"
    )

    ofertas = respuesta.get("data", [])

    if not ofertas:
        print("No se encontraron ofertas.")
        return

    oferta = ofertas[0]

    job = await convertir_oferta(oferta)

    print("\nAnalizando:")
    print(job.title)
    print(job.company)

    resultado = await analizar_oferta(job)

    print("\n===== RESULTADO IA =====")

    print(f"\nMatch: {resultado['match']}%")

    print(f"\nResumen:")
    print(resultado["summary"])

    print("\nFortalezas:")

    for item in resultado["strengths"]:
        print(f"- {item}")

    print("\nFaltantes:")

    for item in resultado["missing"]:
        print(f"- {item}")

    print("\nRazón:")
    print(resultado["reason"])


if __name__ == "__main__":
    asyncio.run(main())