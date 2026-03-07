import re

with open('structured_logger.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Gap 14: Add source field
new_log_entry = '''@dataclass
class LogEntry:
    timestamp: float
    level: str
    message: str
    source: str = "self_improver"  # Gap 14: Telemetry Source Differentiation
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
            "source": self.source,
            "data": self.data
        }
'''

content = re.sub(r'@dataclass\nclass LogEntry:.*?(?=\n\nclass StructuredLogger)', new_log_entry, content, flags=re.DOTALL)

# Add ErrorClassifier for Gap 10
error_classifier_code = '''
class ErrorCategory(str, Enum):
    LLM_OUTPUT_MALFORMED = "LLMOutputMalformed"
    TOOL_CALL_TIMEOUT = "ToolCallTimeout"
    SANDBOX_DENIED = "SandboxPermissionDenied"
    ROUTER_MISMATCH = "RouterMisclassification"
    NETWORK_ERROR = "NetworkError"
    UNKNOWN = "UnknownError"

class ErrorClassifier:
    """Gap 10: Structured Error Classification"""
    @staticmethod
    def classify(error_msg: str) -> ErrorCategory:
        error_msg = str(error_msg).lower()
        if "jsondecodeerror" in error_msg or "expecting value" in error_msg:
            return ErrorCategory.LLM_OUTPUT_MALFORMED
        if "timeout" in error_msg:
            return ErrorCategory.TOOL_CALL_TIMEOUT
        if "permission" in error_msg or "access is denied" in error_msg:
            return ErrorCategory.SANDBOX_DENIED
        if "connection" in error_msg or "socket" in error_msg:
            return ErrorCategory.NETWORK_ERROR
        if "route" in error_msg or "match" in error_msg:
            return ErrorCategory.ROUTER_MISMATCH
        return ErrorCategory.UNKNOWN
'''

if 'class ErrorClassifier' not in content:
    content = content.replace('class StructuredLogger:', error_classifier_code + '\nclass StructuredLogger:')

# Update log methods to accept source and classify errors
content = content.replace('def log(self, level: str, message: str, **kwargs):', 'def log(self, level: str, message: str, source: str = "self_improver", **kwargs):')
content = content.replace('entry = LogEntry(\n            timestamp=time.time(),\n            level=level.upper(),\n            message=message,\n            data=kwargs\n        )', 'entry = LogEntry(\n            timestamp=time.time(),\n            level=level.upper(),\n            message=message,\n            source=source,\n            data=kwargs\n        )')

content = content.replace('def error(self, message: str, error: Exception = None, **kwargs):', 'def error(self, message: str, error: Exception = None, source: str = "self_improver", **kwargs):')
content = content.replace('if error:\n            kwargs["error_type"] = type(error).__name__\n            kwargs["error_details"] = str(error)', 'if error:\n            kwargs["error_type"] = type(error).__name__\n            kwargs["error_details"] = str(error)\n            kwargs["error_category"] = ErrorClassifier.classify(str(error)).value')

with open('structured_logger.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done modifying structured_logger.py')
