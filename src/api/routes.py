"""FastAPI routes for the analytics API"""
import asyncio
from typing import Dict, Any, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from src.utils.logger import logger

router = APIRouter()

# Dependencies (set by main.py)
_camera_manager = None
_metrics_collector = None
_config = None


def set_dependencies(camera_manager, metrics_collector, config):
    """Set module dependencies"""
    global _camera_manager, _metrics_collector, _config
    _camera_manager = camera_manager
    _metrics_collector = metrics_collector
    _config = config


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@router.get("/cameras")
async def list_cameras():
    """List all configured cameras"""
    if _camera_manager is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    cameras = []
    for camera_id, processor in _camera_manager.processors.items():
        cameras.append({
            "id": camera_id,
            "name": processor.config.get("name", camera_id),
            "status": "active" if processor.stream.is_running else "inactive",
            "current_count": processor.current_count
        })
    
    return {"cameras": cameras}


@router.get("/cameras/{camera_id}")
async def get_camera(camera_id: str):
    """Get details for a specific camera"""
    if _camera_manager is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    processor = _camera_manager.get_processor(camera_id)
    if not processor:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    return {
        "id": camera_id,
        "name": processor.config.get("name", camera_id),
        "status": "active" if processor.stream.is_running else "inactive",
        "current_count": processor.current_count,
        "total_footfall": processor.total_footfall,
        "zone_stats": processor.zone_analytics.get_stats(),
        "processed_frames": processor.processed_frames
    }


@router.get("/cameras/{camera_id}/frame")
async def get_camera_frame(camera_id: str):
    """Get latest processed frame as base64"""
    if _camera_manager is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    processor = _camera_manager.get_processor(camera_id)
    if not processor:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    frame_base64 = processor.get_frame_base64()
    if not frame_base64:
        raise HTTPException(status_code=404, detail="No frame available")
    
    return {"camera_id": camera_id, "frame": frame_base64}


@router.get("/cameras/{camera_id}/heatmap")
async def get_camera_heatmap(camera_id: str):
    """Get heatmap for a camera"""
    if _camera_manager is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    processor = _camera_manager.get_processor(camera_id)
    if not processor:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    heatmap_base64 = processor.get_heatmap_base64()
    if not heatmap_base64:
        raise HTTPException(status_code=404, detail="No heatmap available")
    
    return {"camera_id": camera_id, "heatmap": heatmap_base64}


@router.get("/stats")
async def get_all_stats():
    """Get aggregated stats from all cameras"""
    if _camera_manager is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    return {
        "cameras": _camera_manager.get_all_stats(),
        "summary": _metrics_collector.get_summary() if _metrics_collector else {}
    }


@router.get("/zones")
async def get_all_zones():
    """Get zone statistics from all cameras"""
    if _camera_manager is None:
        raise HTTPException(status_code=503, detail="System not initialized")
    
    zones = {}
    for camera_id, processor in _camera_manager.processors.items():
        zones[camera_id] = processor.zone_analytics.get_stats()
    
    return {"zones": zones}


@router.websocket("/ws/stream/{camera_id}")
async def websocket_stream(websocket: WebSocket, camera_id: str):
    """WebSocket endpoint for real-time video stream"""
    await websocket.accept()
    
    if _camera_manager is None:
        await websocket.close(code=1011, reason="System not initialized")
        return
    
    processor = _camera_manager.get_processor(camera_id)
    if not processor:
        await websocket.close(code=1008, reason="Camera not found")
        return
    
    logger.info(f"WebSocket connected for camera {camera_id}")
    
    try:
        while True:
            # Get latest frame and analytics
            frame_base64 = processor.get_frame_base64()
            
            if frame_base64:
                await websocket.send_json({
                    "type": "frame",
                    "camera_id": camera_id,
                    "frame": frame_base64,
                    "current_count": processor.current_count,
                    "zone_stats": processor.zone_analytics.get_stats()
                })
            
            await asyncio.sleep(0.1)  # 10 FPS for WebSocket
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for camera {camera_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


@router.websocket("/ws/analytics")
async def websocket_analytics(websocket: WebSocket):
    """WebSocket endpoint for real-time analytics updates"""
    await websocket.accept()
    
    if _camera_manager is None:
        await websocket.close(code=1011, reason="System not initialized")
        return
    
    logger.info("Analytics WebSocket connected")
    
    try:
        while True:
            # Send aggregated analytics
            await websocket.send_json({
                "type": "analytics",
                "cameras": _camera_manager.get_all_stats(),
                "summary": _metrics_collector.get_summary() if _metrics_collector else {}
            })
            
            await asyncio.sleep(1)  # 1 update per second
            
    except WebSocketDisconnect:
        logger.info("Analytics WebSocket disconnected")
    except Exception as e:
        logger.error(f"Analytics WebSocket error: {e}")