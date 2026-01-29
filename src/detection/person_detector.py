"""Person detection using YOLOv8"""
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False

from src.utils.logger import logger


@dataclass
class Detection:
    """Detection result"""
    bbox: np.ndarray  # [x1, y1, x2, y2]
    confidence: float
    class_id: int
    
    @property
    def center(self) -> tuple:
        return (
            int((self.bbox[0] + self.bbox[2]) / 2),
            int((self.bbox[1] + self.bbox[3]) / 2)
        )


class PersonDetector:
    """YOLOv8-based person detector"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.confidence_threshold = config.get("confidence_threshold", 0.5)
        self.target_classes = config.get("classes", [0])  # 0 = person
        self.model: Optional[Any] = None
        
        self._load_model(config.get("model", "yolov8n"))
    
    def _load_model(self, model_name: str):
        """Load YOLO model"""
        if not YOLO_AVAILABLE:
            logger.warning("YOLO not available. Using dummy detector.")
            return
        
        try:
            self.model = YOLO(f"{model_name}.pt")
            logger.info(f"Loaded YOLO model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load YOLO model: {e}")
            self.model = None
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Detect persons in frame"""
        if self.model is None:
            return self._dummy_detect(frame)
        
        try:
            results = self.model(frame, verbose=False)[0]
            detections = []
            
            for box in results.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                
                if class_id in self.target_classes and confidence >= self.confidence_threshold:
                    bbox = box.xyxy[0].cpu().numpy()
                    detections.append(Detection(
                        bbox=bbox,
                        confidence=confidence,
                        class_id=class_id
                    ))
            
            return detections
            
        except Exception as e:
            logger.error(f"Detection error: {e}")
            return []
    
    def _dummy_detect(self, frame: np.ndarray) -> List[Detection]:
        """Dummy detection for testing without YOLO"""
        # Generate random detections for testing
        import random
        detections = []
        
        h, w = frame.shape[:2]
        num_detections = random.randint(0, 5)
        
        for _ in range(num_detections):
            x1 = random.randint(0, w - 100)
            y1 = random.randint(0, h - 200)
            x2 = x1 + random.randint(50, 100)
            y2 = y1 + random.randint(100, 200)
            
            detections.append(Detection(
                bbox=np.array([x1, y1, x2, y2]),
                confidence=random.uniform(0.5, 1.0),
                class_id=0
            ))
        
        return detections