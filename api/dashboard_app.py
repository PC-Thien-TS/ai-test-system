from __future__ import annotations

from fastapi import FastAPI

from api.routes.dashboard_intelligence import router as dashboard_intelligence_router


def create_app() -> FastAPI:
    app = FastAPI(title="AI Testing Platform Dashboard Intelligence API")
    app.include_router(dashboard_intelligence_router)
    return app


app = create_app()

