# runner/completion_gate.py
from shared.contracts import StepStatus, RunStatus

def compute_status(results: dict, ledger=None) -> RunStatus:
    values = list(results.values())
    if ledger is not None and any(
        status == "UNVERIFIABLE" for _, status in ledger.verify_chain()
    ):
        return RunStatus.ESCALATED
    if any(r.escalated for r in values):
        return RunStatus.ESCALATED
    if any(r.status == StepStatus.STALE for r in values):
        return RunStatus.PARTIAL
    if all(r.status == StepStatus.VERIFIED for r in values):
        return RunStatus.COMPLETE
    if all(r.status != StepStatus.VERIFIED for r in values):
        return RunStatus.FAILED
    return RunStatus.PARTIAL