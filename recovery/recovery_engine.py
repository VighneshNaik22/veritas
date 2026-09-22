# recovery/recovery_engine.py
from dataclasses import dataclass
from shared.contracts import FailureClass

MAX_RETRIES = 3

RECOVERY_MAP = {
    FailureClass.TIMEOUT: "RETRY",
    FailureClass.NO_EFFECT: "RETRY",
    FailureClass.PARTIAL: "RETRY",
    FailureClass.WRONG_VALUE: "REGENERATE_THEN_ESCALATE",
    FailureClass.DUPLICATE: "STOP_DEDUPE",
    FailureClass.COLLATERAL: "ESCALATE",
}

@dataclass
class RecoveryDecision:
    action: str   # "RETRY" | "ESCALATE" | "STOP"

def decide(contract, failure_class: FailureClass, attempts: int) -> RecoveryDecision:
    if not contract.reversible and failure_class != FailureClass.NONE:
        return RecoveryDecision("ESCALATE")

    strategy = RECOVERY_MAP.get(failure_class, "ESCALATE")

    if strategy == "RETRY":
        if attempts < MAX_RETRIES:
            return RecoveryDecision("RETRY")
        return RecoveryDecision("STOP")

    if strategy == "REGENERATE_THEN_ESCALATE":
        if attempts == 1:
            return RecoveryDecision("RETRY")
        return RecoveryDecision("ESCALATE")

    if strategy == "STOP_DEDUPE":
        return RecoveryDecision("STOP")

    return RecoveryDecision("ESCALATE")