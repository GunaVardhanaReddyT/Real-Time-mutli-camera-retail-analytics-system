"""Main entry point for the Retail Analytics System"""
import asyncio
import signal
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.camera.camera_manager import CameraManager
from src.analytics.metrics import MetricsCollector
from src.api.routes import router, set_dependencies
from src.utils.logger import setup_logger, logger
from src.utils.helpers import load_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Retail Analytics System...")
    
    # Load configuration
    config = load_config("config/config.yaml")
    
    # Initialize components
    camera_manager = CameraManager(config)
    metrics_collector = MetricsCollector(config)
    
    # Set dependencies for routes
    set_dependencies(camera_manager, metrics_collector, config)
    
    # Start camera processing
    await camera_manager.start()
    
    logger.info("System started successfully!")
    
    yield
    
    # Cleanup
    logger.info("Shutting down...")
    await camera_manager.stop()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    setup_logger()
    
    app = FastAPI(
        title="Retail Analytics API",
        description="Real-Time Multi-Camera Retail Analytics System",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(router, prefix="/api")
    
    # Serve dashboard
    app.mount("/dashboard", StaticFiles(directory="dashboard", html=True), name="dashboard")
    
    return app


app = create_app()


if __name__ == "__main__":
    config = load_config("config/config.yaml")
    uvicorn.run(
        "src.main:app",
        host=config.get("api", {}).get("host", "0.0.0.0"),
        port=config.get("api", {}).get("port", 8000),
        reload=True
    )