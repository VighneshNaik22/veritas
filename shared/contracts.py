"""
shared/contracts.py
Single source of truth for data shapes used by all three tracks.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import time
import uuid


class StepStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class RunStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class FailureClass(str, Enum):
    NONE = "NONE"
    NO_EFFECT = "NO_EFFECT"
    PARTIAL = "PARTIAL"
    WRONG_VALUE = "WRONG_VALUE"
    DUPLICATE = "DUPLICATE"
    COLLATERAL = "COLLATERAL"
    TIMEOUT = "TIMEOUT"


@dataclass
class StepContract:
    step_id: str
    name: str
    depends_on: list[str]
    tool: str
    args: dict[str, Any]
    expected: dict[str, Any]
    idempotency_key: str
    reversible: bool = True


@dataclass
class ToolResult:
    step_id: str
    claim: str
    raw: dict[str, Any]
    raised_timeout: bool = False


@dataclass
class Evidence:
    evidence_id: str
    step_id: str
    timestamp: float
    check_type: str
    passed: bool
    details: dict[str, Any]
    prev_hash: str
    hash: str


@dataclass
class StepResult:
    step_id: str
    status: StepStatus
    claim: str
    evidence: Optional[Evidence] = None
    failure_class: FailureClass = FailureClass.NONE
    attempts: int = 0
    escalated: bool = False


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def now() -> float:
    return time.time()