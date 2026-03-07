"""
Autopsy - Session analysis and pattern recognition component
Analyzes historical logs to identify patterns and suggest improvements
"""

import json
import re
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class LogEntry:
    """Structured log entry"""
    timestamp: float
    level: str
    message: str
    task_id: Optional[str] = None
    duration: Optional[float] = None
    status: Optional[str] = None
    error: Optional[str] = None
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


@dataclass
class AnalysisResult:
    """Result of autopsy analysis"""
    total_entries: int
    time_range: tuple
    error_rate: float
    avg_execution_time: float
    patterns: List[Dict[str, Any]]
    suggestions: List[str]
    hotspots: List[Dict[str, Any]]
    performance_trends: Dict[str, Any]


class Autopsy:
    """
    Autopsy system for analyzing logs and identifying patterns
    Provides insights for self-improvement
    """
    
    def __init__(self, max_entries: int = 10000, db=None):
        """
        Initialize Autopsy
        
        Args:
            max_entries: Maximum log entries to keep
            db: JarvisDatabase instance for persistent storage
        """
        self.max_entries = max_entries
        self.db = db
        self.logs: List[LogEntry] = []
        self.error_patterns: Counter = Counter()
        self.performance_history: List[float] = []
        self._db_loaded = False
        
    def add_log(self, entry: LogEntry):
        """Add a log entry"""
        self.logs.append(entry)
        
        # Keep only recent logs
        if len(self.logs) > self.max_entries:
            self.logs = self.logs[-self.max_entries:]
        
        # Track errors
        if entry.level == "ERROR":
            self.error_patterns[entry.error or "unknown"] += 1
        
        # Track performance
        if entry.duration is not None:
            self.performance_history.append(entry.duration)
            
        # Asynchronously write to DB
        if self.db and self._db_loaded:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.db.save_log(entry))
            except RuntimeError:
                pass
                
    async def load_state(self):
        """Load historical logs from database across restarts"""
        if self.db:
            historical_logs = await self.db.get_all_logs()
            for log in historical_logs:
                # Add silently without triggering recursive db saving
                self.logs.append(log)
                if log.level == "ERROR":
                    self.error_patterns[log.error or "unknown"] += 1
                if log.duration is not None:
                    self.performance_history.append(log.duration)
            
            # Trim to max
            if len(self.logs) > self.max_entries:
                self.logs = self.logs[-self.max_entries:]
            self._db_loaded = True
    
    def get_error_rate(self) -> float:
        """Calculate error rate"""
        if not self.logs:
            return 0.0
        
        errors = sum(1 for log in self.logs if log.level == "ERROR")
        return errors / len(self.logs)
    
    def get_average_execution_time(self) -> float:
        """Get average execution time"""
        if not self.performance_history:
            return 0.0
        
        return sum(self.performance_history) / len(self.performance_history)
    
    def identify_error_patterns(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Identify most common error patterns"""
        patterns = []
        
        for error, count in self.error_patterns.most_common(top_n):
            percentage = (count / len(self.logs) * 100) if self.logs else 0
            patterns.append({
                "error": error,
                "frequency": count,
                "percentage": round(percentage, 2),
            })
        
        return patterns
    
    def identify_performance_hotspots(self, percentile: float = 0.95) -> List[Dict[str, Any]]:
        """
        Identify slow tasks (performance hotspots)
        
        Args:
            percentile: Percentile threshold (0.95 = 95th percentile)
        """
        if not self.performance_history:
            return []
        
        sorted_times = sorted(self.performance_history)
        threshold = sorted_times[int(len(sorted_times) * percentile)]
        
        hotspots = []
        task_times = defaultdict(list)
        
        for log in self.logs:
            if log.duration and log.duration > threshold and log.task_id:
                task_times[log.task_id].append(log.duration)
        
        for task_id, times in task_times.items():
            avg_time = sum(times) / len(times)
            hotspots.append({
                "task_id": task_id,
                "avg_duration": round(avg_time, 3),
                "occurrences": len(times),
                "severity": "high" if avg_time > threshold * 1.5 else "medium",
            })
        
        return sorted(hotspots, key=lambda x: x["avg_duration"], reverse=True)
    
    def generate_suggestions(self) -> List[str]:
        """Generate improvement suggestions"""
        suggestions = []
        
        # Check error rate
        error_rate = self.get_error_rate()
        if error_rate > 0.1:  # More than 10% errors
            suggestions.append(
                f"High error rate ({error_rate*100:.1f}%). "
                f"Review most common errors: {[p['error'] for p in self.identify_error_patterns(3)]}"
            )
        
        # Check performance
        avg_time = self.get_average_execution_time()
        if avg_time > 10.0:  # More than 10 seconds average
            suggestions.append(
                f"High average execution time ({avg_time:.2f}s). "
                f"Optimize hotspots: {[h['task_id'] for h in self.identify_performance_hotspots(3)]}"
            )
        
        # Check for errors
        if self.error_patterns:
            top_error = self.error_patterns.most_common(1)[0][0]
            suggestions.append(
                f"Most common error is '{top_error}'. "
                f"Implement proper error handling."
            )
        
        return suggestions
    
    def analyze(self) -> AnalysisResult:
        """Perform comprehensive analysis"""
        if not self.logs:
            return AnalysisResult(
                total_entries=0,
                time_range=(None, None),
                error_rate=0.0,
                avg_execution_time=0.0,
                patterns=[],
                suggestions=[],
                hotspots=[],
                performance_trends={},
            )
        
        # Get time range
        time_range = (
            min(log.timestamp for log in self.logs),
            max(log.timestamp for log in self.logs),
        )
        
        # Get performance trends
        performance_trends = self._calculate_performance_trends()
        
        return AnalysisResult(
            total_entries=len(self.logs),
            time_range=time_range,
            error_rate=self.get_error_rate(),
            avg_execution_time=self.get_average_execution_time(),
            patterns=self.identify_error_patterns(),
            suggestions=self.generate_suggestions(),
            hotspots=self.identify_performance_hotspots(),
            performance_trends=performance_trends,
        )
    
    def _calculate_performance_trends(self) -> Dict[str, Any]:
        """Calculate performance improvement/degradation trends"""
        if len(self.performance_history) < 2:
            return {"trend": "insufficient_data"}
        
        # Split history into halves
        mid = len(self.performance_history) // 2
        first_half = self.performance_history[:mid]
        second_half = self.performance_history[mid:]
        
        first_avg = sum(first_half) / len(first_half) if first_half else 0
        second_avg = sum(second_half) / len(second_half) if second_half else 0
        
        improvement = ((first_avg - second_avg) / first_avg * 100) if first_avg > 0 else 0
        
        return {
            "trend": "improving" if improvement > 5 else ("degrading" if improvement < -5 else "stable"),
            "improvement_percentage": round(improvement, 2),
            "early_avg": round(first_avg, 3),
            "recent_avg": round(second_avg, 3),
        }
    
    def export_logs(self, format: str = "json") -> str:
        """Export logs in specified format"""
        if format == "json":
            return json.dumps(
                [asdict(log) for log in self.logs],
                default=str,
                indent=2,
            )
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    def clear_old_logs(self, seconds: int = 86400):
        """Clear logs older than specified seconds"""
        now = datetime.now().timestamp()
        self.logs = [log for log in self.logs if (now - log.timestamp) < seconds]
