from fastapi import FastAPI

from app.api import auth, documents
from app.core.database import init_db
from app.core.search import ensure_index


def create_app() -> FastAPI:
    app = FastAPI(title="Union Knowledge Base (UKB)")
    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(documents.router, prefix="/documents", tags=["documents"])

    @app.on_event("startup")
    def startup() -> None:
        init_db()
        ensure_index()

    return app


app = create_app()
