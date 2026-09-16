"""
Core monitoring, structured logging, and circuit breaker.
Audit events are persisted to the `audit_logs` DB table AND emitted as structured log lines.
"""
import logging
import json
import enum
import time
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────────────────────

class AgentStatusEnum(str, enum.Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    INVALID_SCHEMA = "INVALID_SCHEMA"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class ProviderStatusEnum(str, enum.Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


# ─────────────────────────────────────────────────────────────────────────────
# Structured Logger
# ─────────────────────────────────────────────────────────────────────────────

def get_structured_logger(name: str):
    log = logging.getLogger(name)
    if not log.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        log.addHandler(handler)
        log.setLevel(logging.INFO)
    return log


# ─────────────────────────────────────────────────────────────────────────────
# Audit Event — persists to `audit_logs` DB table
# ─────────────────────────────────────────────────────────────────────────────

async def persist_audit_event(action: str, entity_type: str, entity_id: str, details: dict):
    """
    Writes the audit event to the `audit_logs` DB table.
    Uses its own session to avoid coupling with the caller's transaction.
    """
    try:
        from core.database import AsyncSessionLocal
        from models.models import AuditLog
        import json as _json
        async with AsyncSessionLocal() as db:
            log_entry = AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=str(entity_id),
                details=_json.dumps(details),
            )
            db.add(log_entry)
            await db.commit()
    except Exception as e:
        # Never crash the main pipeline because of audit logging
        logger.warning(f"Failed to persist audit event to DB: {e}")


def log_audit_event(log: logging.Logger, action: str, entity_type: str, entity_id: str, details: dict):
    """
    Standardised audit event:
    - Emits as a structured JSON log line (always synchronous).
    - Schedules a background DB write (fire-and-forget, never blocks caller).
    """
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "details": details,
    }
    log.info(f"AUDIT_EVENT: {json.dumps(event)}")

    # Schedule the DB write without blocking
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(persist_audit_event(action, entity_type, entity_id, details))
        else:
            asyncio.run(persist_audit_event(action, entity_type, entity_id, details))
    except Exception:
        pass  # Never crash the pipeline


# ─────────────────────────────────────────────────────────────────────────────
# Circuit Breaker — CLOSED → OPEN → HALF_OPEN
# ─────────────────────────────────────────────────────────────────────────────

class CircuitBreaker:
    """
    Stateful Circuit Breaker for external providers.

    States:
        CLOSED   — normal operation.
        OPEN     — too many failures; reject calls immediately.
        HALF_OPEN— cooldown elapsed; allow one probe call.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            if self.state != "OPEN":
                logger.warning(f"CircuitBreaker OPENED after {self.failure_count} failures")
            self.state = "OPEN"

    def record_success(self):
        if self.state == "HALF_OPEN":
            logger.info("CircuitBreaker recovered — state → CLOSED")
        self.failure_count = 0
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info("CircuitBreaker cooldown elapsed — state → HALF_OPEN")
                self.state = "HALF_OPEN"
                return True  # allow one probe
            return False
        # HALF_OPEN: allow the one probe
        return True


import time

class CircuitBreaker:
    """Stateful Circuit Breaker for external providers (e.g., Angel One, Yahoo Finance)."""
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def record_success(self):
        self.failure_count = 0
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
            # Allow one execution to see if the provider is healthy again
            return True
            
        return True
