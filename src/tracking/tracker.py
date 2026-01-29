"""Multi-object tracking using SORT-like algorithm"""
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from scipy.optimize import linear_sum_assignment

from src.detection.person_detector import Detection
from src.utils.helpers import calculate_iou
from src.utils.logger import logger


@dataclass
class Track:
    """Tracked object"""
    track_id: int
    bbox: np.ndarray
    confidence: float
    age: int = 0
    hits: int = 1
    time_since_update: int = 0
    trail: List[Tuple[int, int]] = field(default_factory=list)
    
    @property
    def center(self) -> Tuple[int, int]:
        return (
            int((self.bbox[0] + self.bbox[2]) / 2),
            int((self.bbox[1] + self.bbox[3]) / 2)
        )
    
    def update(self, detection: Detection):
        """Update track with new detection"""
        self.bbox = detection.bbox
        self.confidence = detection.confidence
        self.hits += 1
        self.time_since_update = 0
        self.age += 1
        
        # Update trail
        self.trail.append(self.center)
        if len(self.trail) > 50:  # Keep last 50 positions
            self.trail.pop(0)
    
    def predict(self):
        """Predict next position (simple linear prediction)"""
        self.age += 1
        self.time_since_update += 1


class MultiObjectTracker:
    """SORT-inspired multi-object tracker"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.max_age = config.get("max_age", 30)
        self.min_hits = config.get("min_hits", 3)
        self.iou_threshold = config.get("iou_threshold", 0.3)
        
        self.tracks: List[Track] = []
        self.next_id = 1
        self.frame_count = 0
    
    def update(self, detections: List[Detection]) -> List[Track]:
        """Update tracks with new detections"""
        self.frame_count += 1
        
        # Predict existing tracks
        for track in self.tracks:
            track.predict()
        
        # Match detections to tracks
        if len(self.tracks) > 0 and len(detections) > 0:
            matched, unmatched_dets, unmatched_tracks = self._associate_detections(detections)
            
            # Update matched tracks
            for track_idx, det_idx in matched:
                self.tracks[track_idx].update(detections[det_idx])
            
            # Create new tracks for unmatched detections
            for det_idx in unmatched_dets:
                self._create_track(detections[det_idx])
        
        elif len(detections) > 0:
            # No existing tracks, create new ones
            for det in detections:
                self._create_track(det)
        
        # Remove dead tracks
        self.tracks = [
            t for t in self.tracks 
            if t.time_since_update < self.max_age
        ]
        
        # Return confirmed tracks
        return [t for t in self.tracks if t.hits >= self.min_hits]
    
    def _associate_detections(self, detections: List[Detection]) -> Tuple[List, List, List]:
        """Associate detections with existing tracks using Hungarian algorithm"""
        num_tracks = len(self.tracks)
        num_dets = len(detections)
        
        # Compute IOU matrix
        iou_matrix = np.zeros((num_tracks, num_dets))
        
        for t, track in enumerate(self.tracks):
            for d, det in enumerate(detections):
                iou_matrix[t, d] = calculate_iou(track.bbox, det.bbox)
        
        # Use Hungarian algorithm (minimize cost = 1 - IOU)
        cost_matrix = 1 - iou_matrix
        track_indices, det_indices = linear_sum_assignment(cost_matrix)
        
        matched = []
        unmatched_dets = list(range(num_dets))
        unmatched_tracks = list(range(num_tracks))
        
        for t, d in zip(track_indices, det_indices):
            if iou_matrix[t, d] >= self.iou_threshold:
                matched.append((t, d))
                unmatched_dets.remove(d)
                unmatched_tracks.remove(t)
        
        return matched, unmatched_dets, unmatched_tracks
    
    def _create_track(self, detection: Detection) -> Track:
        """Create a new track"""
        track = Track(
            track_id=self.next_id,
            bbox=detection.bbox,
            confidence=detection.confidence
        )
        track.trail.append(track.center)
        
        self.tracks.append(track)
        self.next_id += 1
        
        return track
    
    def reset(self):
        """Reset tracker state"""
        self.tracks = []
        self.next_id = 1
        self.frame_count = 0