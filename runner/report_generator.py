# runner/report_generator.py
from shared.contracts import StepStatus

def build_report(results: dict, run_status) -> str:
    lines = [f"FINAL STATUS: {run_status.value}", ""]
    for step_id, r in results.items():
        if r.status == StepStatus.VERIFIED:
            lines.append(f"[{r.evidence.evidence_id}] {r.claim} -- VERIFIED")
        else:
            reason = r.failure_class.value if r.failure_class else r.status.value
            escal = " -- ESCALATED, needs human approval" if r.escalated else ""
            lines.append(f"[NOT VERIFIED] step '{step_id}' -- {r.status.value} ({reason}){escal}")
    return "\n".join(lines)