from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.database import init_db
from app.routers import employee_router, esg_router, game_router, hr_router, import_router, pair_router, recommendation_router, team_router, wallet_router
from app.services.import_service import seed_demo_data

app = FastAPI(
    title=settings.app_name,
    description="HackAlem AI Career Quest backend for employee development recommendations",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    init_db()
    seed_demo_data()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name}


app.include_router(import_router.router, prefix="/api/import", tags=["import"])
app.include_router(employee_router.router, prefix="/api/employees", tags=["employees"])
app.include_router(recommendation_router.router, prefix="/api", tags=["recommendations"])
app.include_router(game_router.router, prefix="/api/game", tags=["game"])
app.include_router(hr_router.router, prefix="/api/hr", tags=["hr"])
app.include_router(team_router.router, prefix="/api/teams", tags=["teams"])
app.include_router(pair_router.router, prefix="/api/pairs", tags=["pair collaboration"])
app.include_router(wallet_router.router, prefix="/api/wallet", tags=["wallet"])
app.include_router(esg_router.router, prefix="/api/esg-goals", tags=["esg"])
