import asyncio

from app.models import Job

from app.database import (
    obtener_ofertas_pendientes,
    marcar_analizando,
    guardar_analisis,
    devolver_a_pendiente,
    contar_analisis_hoy
)

from services.ai import analizar_oferta


# ==========================================
# CONFIGURACIÓN
# ==========================================

LIMITES_POR_FUENTE = {
    "Get on Board": 5,
    "Job API": 5
}


# ==========================================
# ANALIZADOR
# ==========================================

async def analizar_pendientes(
    limit: int = 10,
    intervalo: int = 30
):

    print("\n🤖 Buscando ofertas pendientes...")

    ofertas = obtener_ofertas_pendientes(
        limit=limit
    )

    print(
        f"📋 Ofertas pendientes encontradas: "
        f"{len(ofertas)}"
    )

    if not ofertas:

        print(
            "ℹ️ No hay ofertas pendientes."
        )

        return

    # ==========================================
    # CONSULTAR CUOTAS
    # ==========================================

    cuotas = {}

    for fuente, limite in LIMITES_POR_FUENTE.items():

        usadas = contar_analisis_hoy(
            fuente
        )

        disponibles = max(
            limite - usadas,
            0
        )

        cuotas[fuente] = {
            "limite": limite,
            "usadas": usadas,
            "disponibles": disponibles
        }

        print(
            f"📊 {fuente}: "
            f"{usadas}/{limite} usados hoy "
            f"→ {disponibles} disponibles"
        )

    # ==========================================
    # ANALIZAR
    # ==========================================

    analizadas = 0
    errores = 0
    omitidas = 0

    for oferta in ofertas:

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
            filter_score
        ) = oferta

        # ==========================================
        # COMPROBAR CUOTA
        # ==========================================

        if source in cuotas:

            if cuotas[source]["disponibles"] <= 0:

                print(
                    f"⏭️ Cuota agotada para "
                    f"{source}: {title}"
                )

                omitidas += 1

                continue

        # ==========================================
        # MOSTRAR OFERTA
        # ==========================================

        print("\n" + "=" * 60)

        print(
            f"🔎 Analizando: {title}"
        )

        print(
            f"🏢 Empresa: {company}"
        )

        print(
            f"📍 Ubicación: {location}"
        )

        print(
            f"📡 Fuente: {source}"
        )

        # ==========================================
        # MARCAR COMO ANALYZING
        # ==========================================

        marcar_analizando(
            job_id
        )

        try:

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
                
                source=source
            )

            # ======================================
            # GROQ
            # ======================================

            resultado = await analizar_oferta(
                job
            )

            # ======================================
            # ERROR / RESPUESTA VACÍA
            # ======================================

            if resultado is None:

                print(
                    "⚠️ Groq no pudo analizar "
                    "la oferta."
                )

                devolver_a_pendiente(
                    job_id
                )

                errores += 1

                continue

            # ======================================
            # GUARDAR ANÁLISIS
            # ======================================

            guardar_analisis(
                job_id=job_id,
                match_score=resultado["match"],
                summary=resultado["summary"],
                strengths=resultado["strengths"],
                missing=resultado["missing"],
                reason=resultado["reason"]
            )

            # ======================================
            # CONSUMIR CUOTA
            # ======================================

            if source in cuotas:

                cuotas[source]["usadas"] += 1

                cuotas[source]["disponibles"] -= 1

            analizadas += 1

            print(
                f"🤖 Match: "
                f"{resultado['match']}%"
            )

            print(
                "✅ Análisis guardado."
            )

        except Exception as e:

            print(
                f"❌ Error analizando "
                f"{title}: {e}"
            )

            devolver_a_pendiente(
                job_id
            )

            errores += 1

        # ==========================================
        # ESPERA
        # ==========================================

        if analizadas > 0:

            print(
                f"⏳ Esperando "
                f"{intervalo} segundos..."
            )

            await asyncio.sleep(
                intervalo
            )

    # ==========================================
    # RESUMEN
    # ==========================================

    print("\n" + "=" * 60)

    print(
        f"🤖 Analizadas: {analizadas}"
    )

    print(
        f"⚠️ Errores: {errores}"
    )

    print(
        f"⏭️ Omitidas por cuota: {omitidas}"
    )

    print("\n📊 CUOTAS DEL DÍA")

    for fuente, datos in cuotas.items():

        print(
            f"   {fuente}: "
            f"{datos['usadas']}/"
            f"{datos['limite']}"
        )

    print("=" * 60)
    return {
        "pendientes": len(ofertas),
        "analizadas": analizadas,
        "errores": errores,
        "omitidas": omitidas,
    }


# ==========================================
# MAIN
# ==========================================

async def main():

    await analizar_pendientes(
        limit=10,
        intervalo=30
    )


if __name__ == "__main__":
    asyncio.run(main())
