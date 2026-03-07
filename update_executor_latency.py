import re

with open('executor.py', 'r', encoding='utf-8') as f:
    content = f.read()

latency_code = '''
class CircuitBreakerError(Exception):
    pass

class CircuitBreaker:
    """Gap 12: Circuit breaker for latency budget"""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        if self.state == "HALF_OPEN":
            return True
        return True

global_circuit_breaker = CircuitBreaker()
'''

if 'class CircuitBreaker' not in content:
    content = content.replace('class Executor:', latency_code + '\nclass Executor:')

latency_check = '''
        if not global_circuit_breaker.can_execute():
            result.status = TaskStatus.FAILED
            result.error = "Circuit Breaker OPEN - Routing to cloud fallback"
            return result

        latency_budget = kwargs.pop('latency_budget', self.timeout)
        try:
            async with self.semaphore:
'''

if 'latency_budget = kwargs.pop' not in content:
    content = content.replace('        try:\n            async with self.semaphore:', latency_check)

success_check = '''
                    if result.execution_time > latency_budget:
                        logger.warning(f"Task {task_id} exceeded latency budget: {result.execution_time} > {latency_budget}")
                        global_circuit_breaker.record_failure()
                    else:
                        global_circuit_breaker.record_success()
                        
            # Fire and forget db save
'''

if 'global_circuit_breaker.record_success' not in content:
    content = content.replace('            # Fire and forget db save', success_check)

with open('executor.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done modifying executor.py for Gap 12')
