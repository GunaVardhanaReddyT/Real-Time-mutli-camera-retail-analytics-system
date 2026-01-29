"""Heatmap generation for traffic patterns"""
import numpy as np
import cv2
from typing import List, Dict, Any, Optional

from src.tracking.tracker import Track


class HeatmapGenerator:
    """Generate foot traffic heatmaps"""
    
    def __init__(self, resolution: Dict[str, int], decay: float = 0.995):
        self.width = resolution.get("width", 1280)
        self.height = resolution.get("height", 720)
        self.decay = decay
        
        # Heatmap accumulator
        self.heatmap = np.zeros((self.height, self.width), dtype=np.float32)
        
    def update(self, tracks: List[Track]):
        """Update heatmap with current track positions"""
        # Apply decay
        self.heatmap *= self.decay
        
        # Add current positions
        for track in tracks:
            cx, cy = track.center
            if 0 <= cx < self.width and 0 <= cy < self.height:
                # Add gaussian blob at position
                self._add_gaussian(cx, cy, sigma=30, intensity=1.0)
    
    def _add_gaussian(self, x: int, y: int, sigma: int = 30, intensity: float = 1.0):
        """Add a gaussian blob to the heatmap"""
        size = sigma * 3
        x_min = max(0, x - size)
        x_max = min(self.width, x + size)
        y_min = max(0, y - size)
        y_max = min(self.height, y + size)
        
        for py in range(y_min, y_max):
            for px in range(x_min, x_max):
                dist_sq = (px - x) ** 2 + (py - y) ** 2
                value = intensity * np.exp(-dist_sq / (2 * sigma ** 2))
                self.heatmap[py, px] = min(1.0, self.heatmap[py, px] + value)
    
    def get_heatmap_image(self, background: Optional[np.ndarray] = None) -> np.ndarray:
        """Get heatmap as colored image"""
        # Normalize heatmap
        normalized = (self.heatmap * 255).astype(np.uint8)
        
        # Apply colormap
        colored = cv2.applyColorMap(normalized, cv2.COLORMAP_JET)
        
        # Blend with background if provided
        if background is not None:
            colored = cv2.addWeighted(background, 0.6, colored, 0.4, 0)
        
        return colored
    
    def get_heatmap_data(self) -> np.ndarray:
        """Get raw heatmap data"""
        return self.heatmap.copy()
    
    def reset(self):
        """Reset heatmap"""
        self.heatmap = np.zeros((self.height, self.width), dtype=np.float32)