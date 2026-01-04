"""FastAPI application entry point with LangSmith setup"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .logging_config import setup_langsmith, logger
from .api.routes import router
from .flow_manager import get_flow_manager
from . import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown"""
    # Startup
    logger.info(f"Starting Sasha Sales AI v{__version__}")
    
    # Initialize settings and setup environment
    settings = get_settings()
    settings.setup_environment()
    
    # Setup LangSmith
    langsmith_client = setup_langsmith()
    if langsmith_client:
        logger.info("LangSmith observability enabled")
    else:
        logger.warning("LangSmith observability disabled")
    
    # Initialize flow manager with Redis
    flow_manager = get_flow_manager()
    logger.info(f"Flow manager initialized, Redis: {flow_manager.redis_url}")
    
    logger.info("Sasha Sales AI started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Sasha Sales AI")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    app = FastAPI(
        title="Sasha Sales AI",
        description="AI-powered sales assistant with LangGraph workflow orchestration",
        version=__version__,
        lifespan=lifespan,
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router, prefix="/api/v1", tags=["sales"])
    
    # Root endpoint
    @app.get("/")
    async def root():
        return {
            "name": "Sasha Sales AI",
            "version": __version__,
            "docs": "/docs",
            "health": "/api/v1/health",
        }
    
    return app


# Create the app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "sasha_sales_ai.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
    )

