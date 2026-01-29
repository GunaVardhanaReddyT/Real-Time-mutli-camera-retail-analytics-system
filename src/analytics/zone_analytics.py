"""Zone-based analytics"""
import time
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from src.tracking.tracker import Track
from src.utils.helpers import point_in_polygon
from src.utils.logger import logger


@dataclass
class ZoneStats:
    """Statistics for a zone"""
    name: str
    current_count: int = 0
    total_entries: int = 0
    total_exits: int = 0
    total_dwell_time: float = 0.0
    avg_dwell_time: float = 0.0
    peak_count: int = 0


@dataclass
class TrackZoneInfo:
    """Track's zone visit information"""
    entry_time: float
    zone_name: str


class ZoneAnalytics:
    """Analyze customer behavior in defined zones"""
    
    def __init__(self, zones_config: List[Dict[str, Any]]):
        self.zones = zones_config
        self.zone_stats: Dict[str, ZoneStats] = {
            zone["name"]: ZoneStats(name=zone["name"])
            for zone in zones_config
        }
        
        # Track which zone each track was last in
        self.track_zones: Dict[int, Optional[TrackZoneInfo]] = {}
        
    def update(self, tracks: List[Track]):
        """Update zone analytics with current tracks"""
        current_time = time.time()
        current_track_ids = set()
        
        # Reset current counts
        for stats in self.zone_stats.values():
            stats.current_count = 0
        
        for track in tracks:
            current_track_ids.add(track.track_id)
            current_zone = self.get_zone_for_point(track.center)
            previous_zone_info = self.track_zones.get(track.track_id)
            
            if current_zone:
                # Increment current count
                self.zone_stats[current_zone].current_count += 1
                
                # Check if this is a new entry
                if previous_zone_info is None or previous_zone_info.zone_name != current_zone:
                    # Exiting previous zone
                    if previous_zone_info:
                        self._handle_zone_exit(track.track_id, previous_zone_info, current_time)
                    
                    # Entering new zone
                    self.zone_stats[current_zone].total_entries += 1
                    self.track_zones[track.track_id] = TrackZoneInfo(
                        entry_time=current_time,
                        zone_name=current_zone
                    )
            else:
                # Track left all zones
                if previous_zone_info:
                    self._handle_zone_exit(track.track_id, previous_zone_info, current_time)
                self.track_zones[track.track_id] = None
        
        # Handle tracks that disappeared
        disappeared_tracks = set(self.track_zones.keys()) - current_track_ids
        for track_id in disappeared_tracks:
            zone_info = self.track_zones.get(track_id)
            if zone_info:
                self._handle_zone_exit(track_id, zone_info, current_time)
            del self.track_zones[track_id]
        
        # Update peak counts
        for stats in self.zone_stats.values():
            if stats.current_count > stats.peak_count:
                stats.peak_count = stats.current_count
    
    def _handle_zone_exit(self, track_id: int, zone_info: TrackZoneInfo, exit_time: float):
        """Handle a track exiting a zone"""
        dwell_time = exit_time - zone_info.entry_time
        stats = self.zone_stats[zone_info.zone_name]
        
        stats.total_exits += 1
        stats.total_dwell_time += dwell_time
        
        if stats.total_exits > 0:
            stats.avg_dwell_time = stats.total_dwell_time / stats.total_exits
    
    def get_zone_for_point(self, point: Tuple[int, int]) -> Optional[str]:
        """Get which zone a point is in"""
        for zone in self.zones:
            if point_in_polygon(point, zone["points"]):
                return zone["name"]
        return None
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get all zone statistics"""
        return {
            name: {
                "current_count": stats.current_count,
                "total_entries": stats.total_entries,
                "total_exits": stats.total_exits,
                "avg_dwell_time": round(stats.avg_dwell_time, 2),
                "peak_count": stats.peak_count
            }
            for name, stats in self.zone_stats.items()
        }