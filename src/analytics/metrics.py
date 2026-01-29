"""Metrics collection and aggregation"""
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta


@dataclass
class TimeSeriesPoint:
    """Single data point in time series"""
    timestamp: datetime
    value: float


class MetricsCollector:
    """Collect and aggregate analytics metrics"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        
        # Time series data
        self.footfall_history: deque = deque(maxlen=3600)  # 1 hour of per-second data
        self.count_history: deque = deque(maxlen=3600)
        
        # Aggregated metrics
        self.total_footfall = 0
        self.peak_occupancy = 0
        self.peak_time: Optional[datetime] = None
        
        # Hourly aggregations
        self.hourly_footfall: Dict[int, int] = {h: 0 for h in range(24)}
        
    def record_count(self, count: int, camera_id: str):
        """Record current occupancy count"""
        now = datetime.now()
        
        self.count_history.append(TimeSeriesPoint(timestamp=now, value=count))
        
        if count > self.peak_occupancy:
            self.peak_occupancy = count
            self.peak_time = now
    
    def record_footfall(self, count: int, camera_id: str):
        """Record footfall entry"""
        now = datetime.now()
        
        self.total_footfall += count
        self.footfall_history.append(TimeSeriesPoint(timestamp=now, value=count))
        self.hourly_footfall[now.hour] += count
    
    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        now = datetime.now()
        
        # Calculate averages
        recent_counts = [p.value for p in self.count_history if now - p.timestamp < timedelta(minutes=5)]
        avg_occupancy = sum(recent_counts) / len(recent_counts) if recent_counts else 0
        
        return {
            "total_footfall": self.total_footfall,
            "peak_occupancy": self.peak_occupancy,
            "peak_time": self.peak_time.isoformat() if self.peak_time else None,
            "current_avg_occupancy": round(avg_occupancy, 1),
            "hourly_footfall": self.hourly_footfall
        }
    
    def get_time_series(self, metric: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get time series data for a metric"""
        now = datetime.now()
        cutoff = now - timedelta(minutes=minutes)
        
        if metric == "count":
            data = self.count_history
        elif metric == "footfall":
            data = self.footfall_history
        else:
            return []
        
        return [
            {"timestamp": p.timestamp.isoformat(), "value": p.value}
            for p in data
            if p.timestamp >= cutoff
        ]