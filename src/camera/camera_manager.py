"""Multi-camera management"""
import asyncio
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from datetime import datetime
import base64

from src.camera.video_stream import VideoStream
from src.detection.person_detector import PersonDetector
from src.tracking.tracker import MultiObjectTracker
from src.analytics.zone_analytics import ZoneAnalytics
from src.analytics.heatmap import HeatmapGenerator
from src.utils.logger import logger


class CameraProcessor:
    """Process frames from a single camera"""
    
    def __init__(self, camera_config: Dict[str, Any], detection_config: Dict[str, Any], tracking_config: Dict[str, Any]):
        self.config = camera_config
        self.camera_id = camera_config["id"]
        self.stream = VideoStream(camera_config)
        self.detector = PersonDetector(detection_config)
        self.tracker = MultiObjectTracker(tracking_config)
        self.zone_analytics = ZoneAnalytics(camera_config.get("zones", []))
        self.heatmap = HeatmapGenerator(
            camera_config.get("resolution", {"width": 1280, "height": 720})
        )
        
        self.current_count = 0
        self.total_footfall = 0
        self.processed_frames = 0
        self.last_processed_frame: Optional[np.ndarray] = None
        
    def start(self) -> bool:
        return self.stream.start()
    
    def stop(self):
        self.stream.stop()
    
    async def process_frame(self) -> Dict[str, Any]:
        """Process a single frame and return analytics"""
        ret, frame = await self.stream.read_async()
        
        if not ret or frame is None:
            return {"error": "No frame available"}
        
        # Detect persons
        detections = self.detector.detect(frame)
        
        # Update tracker
        tracks = self.tracker.update(detections)
        
        # Update analytics
        self.zone_analytics.update(tracks)
        self.heatmap.update(tracks)
        
        # Count people
        self.current_count = len(tracks)
        
        # Draw on frame
        annotated_frame = self._draw_annotations(frame, tracks)
        self.last_processed_frame = annotated_frame
        self.processed_frames += 1
        
        return {
            "camera_id": self.camera_id,
            "timestamp": datetime.now().isoformat(),
            "current_count": self.current_count,
            "tracks": [
                {
                    "id": t.track_id,
                    "bbox": t.bbox.tolist(),
                    "center": t.center,
                    "zone": self.zone_analytics.get_zone_for_point(t.center)
                }
                for t in tracks
            ],
            "zone_stats": self.zone_analytics.get_stats(),
            "total_footfall": self.total_footfall
        }
    
    def _draw_annotations(self, frame: np.ndarray, tracks: List) -> np.ndarray:
        """Draw bounding boxes, tracks, and zones on frame"""
        annotated = frame.copy()
        
        # Draw zones
        for zone in self.config.get("zones", []):
            points = np.array(zone["points"], np.int32)
            cv2.polylines(annotated, [points], True, (0, 255, 255), 2)
            
            # Zone label
            centroid = np.mean(points, axis=0).astype(int)
            cv2.putText(annotated, zone["name"], tuple(centroid), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        
        # Draw tracks
        for track in tracks:
            x1, y1, x2, y2 = map(int, track.bbox)
            
            # Bounding box
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Track ID
            cv2.putText(annotated, f"ID: {track.track_id}", (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            # Trail
            if len(track.trail) > 1:
                for i in range(1, len(track.trail)):
                    cv2.line(annotated, track.trail[i-1], track.trail[i], (255, 0, 0), 2)
        
        # Stats overlay
        cv2.putText(annotated, f"Count: {self.current_count}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(annotated, f"Camera: {self.camera_id}", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        return annotated
    
    def get_frame_base64(self) -> Optional[str]:
        """Get latest processed frame as base64"""
        if self.last_processed_frame is None:
            return None
        
        _, buffer = cv2.imencode('.jpg', self.last_processed_frame)
        return base64.b64encode(buffer).decode('utf-8')
    
    def get_heatmap_base64(self) -> Optional[str]:
        """Get heatmap as base64"""
        heatmap_img = self.heatmap.get_heatmap_image()
        if heatmap_img is None:
            return None
        
        _, buffer = cv2.imencode('.jpg', heatmap_img)
        return base64.b64encode(buffer).decode('utf-8')


class CameraManager:
    """Manage multiple camera processors"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.processors: Dict[str, CameraProcessor] = {}
        self.running = False
        self._process_task: Optional[asyncio.Task] = None
        
        # Initialize processors for each camera
        for cam_config in config.get("cameras", []):
            processor = CameraProcessor(
                cam_config,
                config.get("detection", {}),
                config.get("tracking", {})
            )
            self.processors[cam_config["id"]] = processor
    
    async def start(self):
        """Start all camera processors"""
        self.running = True
        
        for camera_id, processor in self.processors.items():
            if processor.start():
                logger.info(f"Started processor for camera {camera_id}")
            else:
                logger.error(f"Failed to start processor for camera {camera_id}")
        
        # Start processing loop
        self._process_task = asyncio.create_task(self._processing_loop())
    
    async def stop(self):
        """Stop all camera processors"""
        self.running = False
        
        if self._process_task:
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass
        
        for processor in self.processors.values():
            processor.stop()
    
    async def _processing_loop(self):
        """Main processing loop for all cameras"""
        while self.running:
            tasks = [
                processor.process_frame()
                for processor in self.processors.values()
                if processor.stream.is_running
            ]
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            
            await asyncio.sleep(0.033)  # ~30 FPS
    
    def get_processor(self, camera_id: str) -> Optional[CameraProcessor]:
        """Get processor for a specific camera"""
        return self.processors.get(camera_id)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get stats from all cameras"""
        return {
            camera_id: {
                "current_count": proc.current_count,
                "total_footfall": proc.total_footfall,
                "processed_frames": proc.processed_frames,
                "zone_stats": proc.zone_analytics.get_stats()
            }
            for camera_id, proc in self.processors.items()
        }