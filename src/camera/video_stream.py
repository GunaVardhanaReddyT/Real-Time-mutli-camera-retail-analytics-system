"""Video stream handling"""
import cv2
import asyncio
import numpy as np
from typing import Optional, Tuple, Dict, Any
from threading import Thread, Lock
from queue import Queue
from src.utils.logger import logger


class VideoStream:
    """Threaded video stream reader for efficient frame capture"""
    
    def __init__(self, camera_config: Dict[str, Any]):
        self.camera_id = camera_config["id"]
        self.source = camera_config["source"]
        self.name = camera_config["name"]
        self.target_fps = camera_config.get("fps", 30)
        self.resolution = camera_config.get("resolution", {"width": 1280, "height": 720})
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_queue: Queue = Queue(maxsize=10)
        self.running = False
        self.thread: Optional[Thread] = None
        self.lock = Lock()
        self.frame_count = 0
        self.current_frame: Optional[np.ndarray] = None
        
    def start(self) -> bool:
        """Start the video stream"""
        try:
            self.cap = cv2.VideoCapture(self.source)
            
            if not self.cap.isOpened():
                logger.error(f"Failed to open camera {self.camera_id}: {self.source}")
                return False
            
            # Set resolution
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution["width"])
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution["height"])
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            self.running = True
            self.thread = Thread(target=self._capture_loop, daemon=True)
            self.thread.start()
            
            logger.info(f"Camera {self.camera_id} ({self.name}) started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting camera {self.camera_id}: {e}")
            return False
    
    def _capture_loop(self):
        """Continuous frame capture loop"""
        while self.running:
            if self.cap is None:
                break
                
            ret, frame = self.cap.read()
            
            if not ret:
                logger.warning(f"Failed to read frame from camera {self.camera_id}")
                continue
            
            with self.lock:
                self.current_frame = frame
                self.frame_count += 1
            
            # Clear old frames if queue is full
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except:
                    pass
            
            self.frame_queue.put(frame)
    
    def read(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Read the latest frame"""
        with self.lock:
            if self.current_frame is None:
                return False, None
            return True, self.current_frame.copy()
    
    async def read_async(self) -> Tuple[bool, Optional[np.ndarray]]:
        """Async frame read"""
        return await asyncio.get_event_loop().run_in_executor(None, self.read)
    
    def stop(self):
        """Stop the video stream"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
        logger.info(f"Camera {self.camera_id} stopped")
    
    @property
    def is_running(self) -> bool:
        return self.running and self.cap is not None and self.cap.isOpened()