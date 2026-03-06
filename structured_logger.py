"""
Structured Logger - Comprehensive logging system
Provides structured, queryable logs with multiple output formats
"""

import logging
import json
import sys
from typing import Any, Dict, Optional
from datetime import datetime
import traceback


class StructuredFormatter(logging.Formatter):
    """Formatter that outputs structured JSON logs"""
    
    def __init__(self, include_timestamp: bool = True):
        """
        Initialize formatter
        
        Args:
            include_timestamp: Include timestamp in logs
        """
        super().__init__()
        self.include_timestamp = include_timestamp
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        log_data = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if self.include_timestamp:
            log_data["timestamp"] = datetime.fromtimestamp(record.created).isoformat()
        
        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info),
            }
        
        # Include extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class StructuredLogger:
    """
    Structured logging system
    Provides methods for logging with structured data
    """
    
    def __init__(self, name: str, level: str = "INFO"):
        """
        Initialize structured logger
        
        Args:
            name: Logger name
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Add console handler with structured formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)
    
    def log_task_start(
        self,
        task_id: str,
        task_type: str,
        params: Dict[str, Any],
    ):
        """Log task start"""
        self._log_with_extra(
            logging.INFO,
            f"Task started: {task_id}",
            {
                "event": "task_start",
                "task_id": task_id,
                "task_type": task_type,
                "params": params,
            }
        )
    
    def log_task_complete(
        self,
        task_id: str,
        duration: float,
        result: Any,
    ):
        """Log task completion"""
        self._log_with_extra(
            logging.INFO,
            f"Task completed: {task_id}",
            {
                "event": "task_complete",
                "task_id": task_id,
                "duration": duration,
                "result_type": type(result).__name__,
            }
        )
    
    def log_task_error(
        self,
        task_id: str,
        error: Exception,
        duration: float,
    ):
        """Log task error"""
        self._log_with_extra(
            logging.ERROR,
            f"Task failed: {task_id}",
            {
                "event": "task_error",
                "task_id": task_id,
                "error": str(error),
                "error_type": type(error).__name__,
                "duration": duration,
            },
            exc_info=True,
        )
    
    def log_performance(
        self,
        metric_name: str,
        value: float,
        unit: str = "",
        tags: Optional[Dict[str, str]] = None,
    ):
        """Log performance metric"""
        extra = {
            "event": "performance",
            "metric": metric_name,
            "value": value,
            "unit": unit,
        }
        if tags:
            extra["tags"] = tags
        
        self._log_with_extra(logging.INFO, f"Performance: {metric_name}={value}{unit}", extra)
    
    def log_analysis(
        self,
        analysis_type: str,
        results: Dict[str, Any],
    ):
        """Log analysis results"""
        self._log_with_extra(
            logging.INFO,
            f"Analysis: {analysis_type}",
            {
                "event": "analysis",
                "type": analysis_type,
                "results": results,
            }
        )
    
    def log_mutation(
        self,
        mutation_id: str,
        category: str,
        description: str,
        confidence: float,
    ):
        """Log instruction mutation"""
        self._log_with_extra(
            logging.INFO,
            f"Mutation: {category}",
            {
                "event": "mutation",
                "mutation_id": mutation_id,
                "category": category,
                "description": description,
                "confidence": confidence,
            }
        )
    
    def log_custom(
        self,
        level: str,
        message: str,
        **extra_fields,
    ):
        """Log with custom fields"""
        log_level = getattr(logging, level.upper(), logging.INFO)
        self._log_with_extra(log_level, message, extra_fields)
    
    def _log_with_extra(
        self,
        level: int,
        message: str,
        extra_fields: Dict[str, Any],
        exc_info: bool = False,
    ):
        """Log with extra fields"""
        # Create a log record manually to include extra fields
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn="",
            lno=0,
            msg=message,
            args=(),
            exc_info=exc_info,
        )
        
        # Attach extra fields
        record.extra_fields = extra_fields
        
        # Log the record
        self.logger.handle(record)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, extra={"extra_fields": kwargs})
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, extra={"extra_fields": kwargs})
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, extra={"extra_fields": kwargs})
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, extra={"extra_fields": kwargs})
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, extra={"extra_fields": kwargs})
