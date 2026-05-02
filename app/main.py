import logging
from collections.abc import AsyncGenerator
from typing import Any

from sqlmodel import SQLModel
import uvicorn
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from uvicorn.config import LOGGING_CONFIG

from app.api.main import api_router
from app.core.config import settings
from app.utils import custom_generate_unique_id

logger = logging.getLogger("uvicorn")


def register_models():
    # Importing these attaches tables to SQLModel.metadata (side effects)
    if not SQLModel.metadata.tables:
        import app.models  # noqa: F401

        logger.info("Models registered to SQLModel metadata.")
    else:
        logger.info("Models already registered.")

    return True


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:  # noqa ARG001
    """life span events"""
    try:
        logger.info("lifespan start")
        # Register models to SQLModel metadata
        register_models()
        yield
    finally:
        logger.info("lifespan exit")


# init FastAPI with lifespan
app = FastAPI(
    lifespan=lifespan,
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    generate_unique_id_function=custom_generate_unique_id,
)


# Set all CORS enabled origins
if settings.all_cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.all_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Include the routers
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["root"])
async def read_root() -> str:
    return "Welcome to the Finforum API!"


# Logger
def timestamp_log_config(uvicorn_log_config: dict[str, Any]) -> dict[str, Any]:
    datefmt = "%d-%m-%Y %H:%M:%S"
    formatters = uvicorn_log_config["formatters"]
    formatters["default"]["fmt"] = "%(levelprefix)s [%(asctime)s] %(message)s"
    formatters["access"]["fmt"] = (
        '%(levelprefix)s [%(asctime)s] %(client_addr)s - "%(request_line)s" %(status_code)s'
    )
    formatters["access"]["datefmt"] = datefmt
    formatters["default"]["datefmt"] = datefmt
    return uvicorn_log_config


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.PORT,
        log_config=timestamp_log_config(LOGGING_CONFIG),
    )
