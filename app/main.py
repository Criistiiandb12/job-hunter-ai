import asyncio
import os
from datetime import datetime

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.auth import crear_token, validar_credenciales, validar_token
from app.database import obtener_ejecuciones_web, obtener_estadisticas_web, obtener_ofertas_web
from services.collector import recolectar_ofertas
from services.message_formatter import crear_mensaje
from services.run_pipeline import main as ejecutar_pipeline

load_dotenv()

app = FastAPI(title="Job Hunter IA", description="Recolector y filtrador de ofertas para Colombia", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("WEB_ORIGINS", "http://localhost:5173").split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

pipeline_task: asyncio.Task | None = None


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def _run_to_dict(row):
    return {
        "id": row[0], "started_at": _iso(row[1]), "ended_at": _iso(row[2]),
        "status": row[3], "found_count": row[4], "filtered_count": row[5],
        "analyzed_count": row[6], "notified_count": row[7], "error_message": row[8],
        "current_step": row[9], "phase_message": row[10], "updated_at": _iso(row[11]),
    }


class LoginRequest(BaseModel):
    username: str
    password: str


def require_admin(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Autenticación requerida")
    if not validar_token(authorization.removeprefix("Bearer ").strip()):
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")


async def _ejecutar_pipeline_en_segundo_plano():
    global pipeline_task
    try:
        await ejecutar_pipeline()
    except Exception as error:
        print(f"Pipeline lanzado desde la web terminó con error: {error}")
    finally:
        pipeline_task = None


@app.post("/api/auth/login")
def login(data: LoginRequest):
    try:
        valid = validar_credenciales(data.username, data.password)
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
    if not valid:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    return {"access_token": crear_token(data.username), "token_type": "bearer", "expires_in": 28800}


@app.get("/api/jobs")
def api_jobs(limit: int = Query(default=50, ge=1, le=100)):
    rows = obtener_ofertas_web(limit)
    return [
        {
            "id": row[0], "title": row[1], "company": row[2], "location": row[3],
            "description": row[4], "source": row[5], "url": row[6],
            "salary_min": row[7], "salary_max": row[8], "remote": row[9],
            "filter_score": row[10], "match_score": row[11], "status": row[12],
            "analyzed_at": _iso(row[13]), "sent_at": _iso(row[14]),
            "ai_summary": row[15], "ai_strengths": row[16], "ai_missing": row[17], "ai_reason": row[18],
            "telegram_message": crear_mensaje((row[0], row[1], row[5], row[6], row[11], row[15], row[16], row[17], row[18])),
        }
        for row in rows
    ]


@app.get("/api/runs")
def api_runs(limit: int = Query(default=20, ge=1, le=100), _: None = Depends(require_admin)):
    return [_run_to_dict(row) for row in obtener_ejecuciones_web(limit)]


@app.post("/api/pipeline/run", status_code=202)
async def api_run_pipeline(_: None = Depends(require_admin)):
    global pipeline_task
    if pipeline_task and not pipeline_task.done():
        raise HTTPException(status_code=409, detail="Ya hay un pipeline ejecutándose")
    pipeline_task = asyncio.create_task(_ejecutar_pipeline_en_segundo_plano())
    return {"status": "started", "message": "Pipeline iniciado"}


@app.get("/api/stats")
def api_stats():
    found_today, compatible, sent_today, getonbrd, jobapi = obtener_estadisticas_web()
    latest = obtener_ejecuciones_web(1)
    return {
        "found_today": found_today or 0, "compatible": compatible or 0,
        "sent_today": sent_today or 0, "telegram_limit": 10,
        "sources": {"Get on Board": getonbrd or 0, "Job API": jobapi or 0},
        "latest_run": _run_to_dict(latest[0]) if latest else None,
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "Job Hunter IA"}


@app.get("/search")
async def search_jobs(query: str = Query(default="python"), country_code: str = Query(default="CO"), incluir_jobapi: bool = Query(default=True)):
    """Recolecta y puntúa usando el flujo normal del proyecto."""
    resultado = await recolectar_ofertas(query=query, country_code=country_code, incluir_jobapi=incluir_jobapi)
    return {"query": query, "country_code": country_code, **resultado}
