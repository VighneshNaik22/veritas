# runner/completion_gate.py
from shared.contracts import StepStatus, RunStatus

def compute_status(results: dict) -> RunStatus:
    values = list(results.values())
    if any(r.escalated for r in values):
        return RunStatus.ESCALATED
    if all(r.status == StepStatus.VERIFIED for r in values):
        return RunStatus.COMPLETE
    if all(r.status != StepStatus.VERIFIED for r in values):
        return RunStatus.FAILED
    return RunStatus.PARTIAL