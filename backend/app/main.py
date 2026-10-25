from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.core.config import settings
from app.api.routes import cameras, analytics, events
from app.api import ws


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    gpu_name: str
    version: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize database, verify configurations
    yield
    # Shutdown: clean up workers and connections


app = FastAPI(
    title="Metro Safety AI - Modular Monolith API",
    version=settings.version,
    description="Computer Vision passenger detection, tracking, crowd analytics and alert monitoring.",
    openapi_url="/contracts/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS configuration for Next.js dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health_check():
    """Process health and runtime readiness check. Does not execute model inference."""
    return HealthResponse(
        status="ok",
        model_loaded=False,
        gpu_name="NVIDIA GeForce RTX 5060 Laptop GPU",
        version=settings.version
    )


# Register API v1 routes
app.include_router(cameras.router, prefix=settings.api_prefix)
app.include_router(analytics.router, prefix=settings.api_prefix)
app.include_router(events.router, prefix=settings.api_prefix)
app.include_router(ws.router, prefix=settings.api_prefix)
