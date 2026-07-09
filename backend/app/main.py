"""Application entry point: builds and configures the FastAPI app."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import academic, assistant, health, pdf, study_tools, youtube
from app.core.config import settings
from app.core.database import init_db
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""

    configure_logging()
    logger = logging.getLogger(__name__)

    init_db()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(pdf.router)
    app.include_router(youtube.router)
    app.include_router(study_tools.router)
    app.include_router(academic.router)
    app.include_router(assistant.router)

    logger.info("%s started in %s mode", settings.app_name, settings.environment)
    return app


app = create_app()
