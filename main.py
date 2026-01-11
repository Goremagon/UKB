from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from pathlib import Path

from app.api import admin, auth, documents
from app.core.database import init_db
from app.core.search import ensure_index


def create_app() -> FastAPI:
    app = FastAPI(title="Union Knowledge Base (UKB)")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(documents.router, prefix="/documents", tags=["documents"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])

    ui_dist = Path(__file__).resolve().parent / "ui" / "dist"
    if ui_dist.exists():
        app.mount("/", StaticFiles(directory=ui_dist, html=True), name="ui")

    @app.on_event("startup")
    def startup() -> None:
        init_db()
        ensure_index()

    return app


app = create_app()
