# AGENT.md — VERITAS, Member 3: Agent + Demo Layer (Plan, Tools, Fault Injection, Dashboard, main.py)

You are helping build **your one-third** of a hackathon project called
VERITAS, for problem statement A1: *"Evidence-Gated Self-Healing Agent
Workflow — design a zero-trust AI agent that executes multi-step tasks,
verifies every action using machine-checkable evidence, detects failures,
and safely recovers or re-plans without falsely claiming completion."*

Team of 3, 5–6 hours total. This file is everything you need. Stick to it
exactly; do not add scope from bigger reference docs (Ed25519 signing,
Merkle trees, ZK proofs, Streamlit, Docker — all explicitly cut, see §1).
**You also own `main.py` — the file that wires all three tracks together
and IS the demo — so read this whole file even if your code is done early.**

---

## 1. Scope reality check (read this first)

Reference docs for this problem statement describe 20+ hour builds for
4–5 people, with a real LLM planner, Streamlit dashboards, Docker, and (in
one version) ZK proofs and a "multi-agent swarm." **None of that fits 5–6
hours with 3 people.** Cuts relevant to your track specifically:

| Cut | Replaced with |
|---|---|
| LLM-based planner | A hard-coded plan (`agent/plan.py`) — still a real DAG with contracts, no API key risk mid-demo |
| Streamlit web dashboard | Rich terminal dashboard only |
| Docker | `python main.py`, nothing else |
| Real LLM-generated executor claims | Templated claim strings — swap in a real LLM call later ONLY if everything else already works with time to spare |

Your job (**agent + demo layer**) is what judges actually see. It has to
run cleanly live — don't add an external API call you can't guarantee
works on the wifi in the room.

---

## 2. What VERITAS is (whole-project context)

**Demo task:** "Process refund for customer C123: verify eligibility,
update the refund DB, send confirmation email, log audit trail."

**4 steps, one linear chain:**
1. `check_eligibility` (C123)
2. `update_refund_db` (R123, $50.00) — **the only step fault injection targets**
3. `send_confirmation_email` — irreversible, never blindly retried
4. `log_audit`

**Why every fault mode targets step 2 only:** if step 2 doesn't verify,
steps 3 and 4 are `BLOCKED` by Member 2's DAG runner — meaning the
irreversible email never gets sent on a bad run. That's your single best
demo line.

```
YOUR CODE: PLAN (hard-coded DAG) → DAG RUNNER (Member 2)
                                          │
                                          ▼
                      YOUR CODE: EXECUTOR (+ FAULT INJECTOR)
                         runs the tool, returns a CLAIM
                                          │
                                          ▼
                      verifier.verify() + classify()   (Member 1)
                                          │
                                          ▼
                      recovery_engine.decide()          (Member 2)
                                          │
                                          ▼
                      completion_gate.compute_status()  (Member 2)
                      report_generator.build_report()   (Member 2)
                                          │
                                          ▼
              YOUR CODE: CLAIM-VS-TRUTH DASHBOARD + fault-sweep METRICS TABLE
              YOUR CODE: main.py ties every piece above together
```

**You own the top third: what the agent actually does, how failures get
injected to prove the system works, and everything a judge looks at.**

---

## 3. Shared contract — `shared/contracts.py` (identical for all 3 members)

Create this file first (or copy it if a teammate already has). Nobody
changes field names after the first 20 minutes without telling the other
two.

```python
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
```

You also need Member 1's `db/schema.sql` + `db/connection.py` (identical
copy is in their file) — you call `build_fresh_world()` and `get_rw_conn()`
from it. You don't need to rebuild it, just import it.

---

## 4. Your deliverable 1 — `agent/plan.py` (the hard-coded DAG)

```python
# agent/plan.py
from shared.contracts import StepContract

DEMO_PLAN = [
    StepContract(
        step_id="step_1", name="check_eligibility", depends_on=[],
        tool="check_eligibility", args={"customer_id": "C123"},
        expected={"eligible": 1}, idempotency_key="elig-C123",
    ),
    StepContract(
        step_id="step_2", name="update_refund_db", depends_on=["step_1"],
        tool="update_refund_db",
        args={"refund_id": "R123", "customer_id": "C123", "amount": 50.00},
        expected={"amount": 50.00, "status": "processed"},
        idempotency_key="refund-R123", reversible=True,
    ),
    StepContract(
        step_id="step_3", name="send_confirmation_email", depends_on=["step_2"],
        tool="send_confirmation_email",
        args={"customer_id": "C123", "refund_id": "R123"},
        expected={}, idempotency_key="email-R123",
        reversible=False,   # an email that left the building can't be unsent
    ),
    StepContract(
        step_id="step_4", name="log_audit", depends_on=["step_3"],
        tool="log_audit",
        args={"step_id": "refund_flow", "message": "refund R123 processed and emailed"},
        expected={}, idempotency_key="audit-refund_flow",
    ),
]
```

---

## 5. Your deliverable 2 — `agent/tools.py`

The `update_refund_db` tool **must be idempotent** (UPSERT, not blind
INSERT) — a retry after a wrong-value fault will hit the same primary key
twice, and a plain INSERT would crash with a duplicate-key error.

```python
# agent/tools.py
import datetime
from shared.contracts import new_id

def check_eligibility(rw_conn, args):
    row = rw_conn.execute("SELECT eligible FROM customers WHERE customer_id=?",
                           (args["customer_id"],)).fetchone()
    return {"status": "success" if row else "not_found"}

def update_refund_db(rw_conn, args):
    existing = rw_conn.execute(
        "SELECT 1 FROM refunds WHERE refund_id=?", (args["refund_id"],)
    ).fetchone()
    if existing:
        rw_conn.execute(
            "UPDATE refunds SET amount=?, status=?, idempotency_key=? WHERE refund_id=?",
            (args["amount"], "processed", args.get("idempotency_key"), args["refund_id"]),
        )
    else:
        rw_conn.execute(
            "INSERT INTO refunds (refund_id, customer_id, amount, status, idempotency_key) "
            "VALUES (?,?,?,?,?)",
            (args["refund_id"], args["customer_id"], args["amount"], "processed",
             args.get("idempotency_key")),
        )
    rw_conn.commit()
    return {"status": "success"}

def send_confirmation_email(rw_conn, args):
    rw_conn.execute(
        "INSERT INTO sent_emails (email_id, customer_id, refund_id, subject, sent_at) "
        "VALUES (?,?,?,?,?)",
        (new_id("MAIL"), args["customer_id"], args["refund_id"], "Your refund is processed",
         datetime.datetime.utcnow().isoformat()),
    )
    rw_conn.commit()
    return {"status": "success"}

def log_audit(rw_conn, args):
    rw_conn.execute(
        "INSERT INTO audit_log (log_id, step_id, message, logged_at) VALUES (?,?,?,?)",
        (new_id("LOG"), args["step_id"], args["message"], datetime.datetime.utcnow().isoformat()),
    )
    rw_conn.commit()
    return {"status": "success"}

TOOL_REGISTRY = {
    "check_eligibility": check_eligibility,
    "update_refund_db": update_refund_db,
    "send_confirmation_email": send_confirmation_email,
    "log_audit": log_audit,
}
```

---

## 6. Your deliverable 3 — `harness/fault_injection.py`

This wraps a real tool call and optionally corrupts the outcome. Build in
this exact order — cut from the bottom if you're short on time.

```python
# harness/fault_injection.py
from shared.contracts import ToolResult

class FaultInjector:
    """fault_map: {step_id: fault_mode}, e.g. {"step_2": "WRONG_VALUE"}"""
    def __init__(self, fault_map: dict | None = None):
        self.fault_map = fault_map or {}
        self._timeout_used: set = set()

    def call(self, tool_fn, rw_conn, contract) -> ToolResult:
        mode = self.fault_map.get(contract.step_id)

        # 1. build this first -- proves zero-trust catches a lying tool
        if mode == "GHOST_SUCCESS":
            return ToolResult(contract.step_id,
                               claim=f"{contract.name} completed successfully.",
                               raw={"status": "success"})   # tool_fn is NEVER called

        # 2. build this second -- proves self-healing / verify-before-retry
        if mode == "TIMEOUT_THEN_RECOVER" and contract.step_id not in self._timeout_used:
            self._timeout_used.add(contract.step_id)
            return ToolResult(contract.step_id, claim="(timed out)", raw={},
                               raised_timeout=True)

        # 3. build this third -- proves evidence-gating catches wrong data, not just missing data
        if mode == "WRONG_VALUE" and contract.tool == "update_refund_db":
            bad_args = dict(contract.args)
            bad_args["amount"] = round(bad_args["amount"] / 10, 2)  # silently wrong
            raw = tool_fn(rw_conn, bad_args)
            return ToolResult(contract.step_id,
                               claim=f"Refund of {contract.args['amount']} processed.",
                               raw=raw)

        # 4. STRETCH -- build last, cut first if short on time
        if mode == "COLLATERAL" and contract.tool == "update_refund_db":
            raw = tool_fn(rw_conn, contract.args)
            rw_conn.execute("UPDATE customers SET eligible=0 WHERE customer_id!=?",
                             (contract.args["customer_id"],))
            rw_conn.commit()
            return ToolResult(contract.step_id,
                               claim=f"{contract.name} completed successfully.", raw=raw)

        # no fault: run for real
        raw = tool_fn(rw_conn, contract.args)
        return ToolResult(contract.step_id,
                           claim=f"{contract.name} completed successfully.", raw=raw)
```

---

## 7. Your deliverable 4 — `agent/executor.py`

```python
# agent/executor.py
from agent.tools import TOOL_REGISTRY

class Executor:
    def __init__(self, rw_conn, fault_injector):
        self.rw_conn = rw_conn
        self.fault_injector = fault_injector

    def execute(self, contract):
        tool_fn = TOOL_REGISTRY[contract.tool]
        return self.fault_injector.call(tool_fn, self.rw_conn, contract)
```

---

## 8. Your deliverable 5 — `harness/baseline_agents.py`

The naive agent is your comparison point — it's what most agents actually
do today (trust the tool's own word), and it's what makes your headline
metric meaningful.

```python
# harness/baseline_agents.py
from shared.contracts import RunStatus

class NaiveAgent:
    """Trusts the executor's own claim. Never independently verifies.
    Exists only to measure how bad 'trust the tool' really is."""
    def __init__(self, executor):
        self.executor = executor

    def run(self, plan):
        claims = []
        for contract in plan:
            result = self.executor.execute(contract)
            claims.append(result)
        claimed_complete = all(r.raw.get("status") == "success" for r in claims)
        status = RunStatus.COMPLETE if claimed_complete else RunStatus.FAILED
        return status, claims


def ground_truth_check(ro_conn) -> bool:
    """Deliberately SEPARATE code from verifier/checker.py -- scoring must
    never share a code path with the thing being graded."""
    refund = ro_conn.execute(
        "SELECT amount, status FROM refunds WHERE refund_id='R123'"
    ).fetchone()
    email = ro_conn.execute(
        "SELECT COUNT(*) FROM sent_emails WHERE refund_id='R123'"
    ).fetchone()[0]
    audit = ro_conn.execute(
        "SELECT COUNT(*) FROM audit_log WHERE step_id='refund_flow'"
    ).fetchone()[0]
    return bool(refund and refund[0] == 50.00 and refund[1] == "processed"
                and email >= 1 and audit >= 1)
```

---

## 9. Your deliverable 6 — `harness/metrics.py`

```python
# harness/metrics.py
FAULT_MODES = ["GHOST_SUCCESS", "TIMEOUT_THEN_RECOVER", "WRONG_VALUE", "COLLATERAL"]

def run_comparison(build_fresh_world, run_naive, run_veritas):
    """build_fresh_world() resets DB + ledger between every run so runs
    never leak into each other. run_naive/run_veritas each take a
    fault_map and return (status, ground_truth_bool)."""
    rows = []
    for mode in ["CLEAN"] + FAULT_MODES:
        fault_map = {} if mode == "CLEAN" else {"step_2": mode}

        build_fresh_world()
        naive_status, naive_truth = run_naive(fault_map)

        build_fresh_world()
        veritas_status, veritas_truth = run_veritas(fault_map)

        rows.append({
            "mode": mode,
            "naive_false_claim": (naive_status.value == "COMPLETE") and not naive_truth,
            "veritas_false_claim": (veritas_status.value == "COMPLETE") and not veritas_truth,
            "veritas_status": veritas_status.value,
        })

    naive_rate = sum(r["naive_false_claim"] for r in rows) / len(rows)
    veritas_rate = sum(r["veritas_false_claim"] for r in rows) / len(rows)
    return rows, naive_rate, veritas_rate
```

Drop `"COLLATERAL"` from `FAULT_MODES` if Member 1 didn't finish the
collateral check in time — 3 clean fault modes beat 4 shaky ones.

---

## 10. Your deliverable 7 — `dashboard/terminal_view.py`

```python
# dashboard/terminal_view.py
from rich.console import Console
from rich.table import Table
from shared.contracts import StepStatus

console = Console()
STATUS_STYLE = {"VERIFIED": "bold green", "FAILED": "bold red", "BLOCKED": "bold yellow"}

def render_claim_vs_truth(results: dict):
    table = Table(title="CLAIM vs TRUTH")
    table.add_column("Step"); table.add_column("Agent Claims")
    table.add_column("System Truth"); table.add_column("Status")
    for step_id, r in results.items():
        truth = "matches" if r.status == StepStatus.VERIFIED else \
            f"MISMATCH -- {r.failure_class.value if r.failure_class else ''}"
        style = STATUS_STYLE.get(r.status.value, "white")
        row_style = "on red" if (r.status != StepStatus.VERIFIED
                                  and "success" in (r.claim or "").lower()) else None
        table.add_row(step_id, r.claim or "-", truth,
                      f"[{style}]{r.status.value}[/{style}]", style=row_style)
    console.print(table)

def render_final_banner(run_status):
    color = {"COMPLETE": "green", "PARTIAL": "yellow",
             "FAILED": "red", "ESCALATED": "magenta"}[run_status.value]
    console.rule(f"[bold {color}]FINAL STATUS: {run_status.value}[/bold {color}]")

def render_metrics_table(rows, naive_rate, veritas_rate):
    table = Table(title="False-Claim Rate: Naive vs VERITAS")
    table.add_column("Fault Mode"); table.add_column("Naive False Claim?")
    table.add_column("VERITAS False Claim?"); table.add_column("VERITAS Final Status")
    for r in rows:
        table.add_row(r["mode"], str(r["naive_false_claim"]),
                      str(r["veritas_false_claim"]), r["veritas_status"])
    console.print(table)
    console.print(f"[bold]Headline -- Naive: {naive_rate:.0%} false claims | "
                   f"VERITAS: {veritas_rate:.0%} false claims[/bold]")
```

`pip install rich` — that's the only dependency this whole project needs
beyond the standard library.

---

## 11. Your deliverable 8 — `main.py` (you own the integration point)

```python
# main.py
import sqlite3
from db.connection import build_fresh_world, get_rw_conn, get_ro_conn
from agent.plan import DEMO_PLAN
from agent.executor import Executor
from harness.fault_injection import FaultInjector
from verifier.independent_verifier import IndependentVerifier
from verifier.failure_classifier import classify
from ledger.evidence_ledger import EvidenceLedger
from recovery import recovery_engine
from runner.dag_runner import DagRunner
from runner.completion_gate import compute_status
from runner.report_generator import build_report
from dashboard.terminal_view import render_claim_vs_truth, render_final_banner

def run_veritas(fault_map):
    rw = get_rw_conn()
    ro = get_ro_conn()
    ledger = EvidenceLedger()
    executor = Executor(rw, FaultInjector(fault_map))
    verifier = IndependentVerifier(ro, ledger)
    runner = DagRunner(executor, verifier, classify, recovery_engine)
    results = runner.run(DEMO_PLAN)
    status = compute_status(results)
    return status, results

if __name__ == "__main__":
    build_fresh_world()
    status, results = run_veritas({"step_2": "GHOST_SUCCESS"})
    render_claim_vs_truth(results)
    render_final_banner(status)
    print(build_report(results, status))
```

**Change the `fault_map` argument to try each mode** (`{}` for clean,
`{"step_2": "TIMEOUT_THEN_RECOVER"}`, `{"step_2": "WRONG_VALUE"}`, etc.)
while you're testing — that's literally your whole demo, just running it
live with different fault maps.

For the full comparison table, write a second small script
`run_metrics.py` that imports `harness.metrics.run_comparison`, wraps
`run_veritas` and a `NaiveAgent` run into the two callables it expects
(each returning `(status, ground_truth_check(get_ro_conn()))`), and prints
the result with `render_metrics_table`.

---

## 12. Stub to use immediately (don't wait for Member 1 or 2)

Before their real code exists, test your executor + fault injector + plan
standing alone:

```python
from db.connection import build_fresh_world, get_rw_conn
from agent.plan import DEMO_PLAN
from agent.executor import Executor
from harness.fault_injection import FaultInjector

build_fresh_world()
rw = get_rw_conn()
ex = Executor(rw, FaultInjector({"step_2": "GHOST_SUCCESS"}))
for step in DEMO_PLAN:
    result = ex.execute(step)
    print(step.step_id, result.claim, result.raw)
# check the DB by hand: refunds table should be EMPTY after step_2
# because GHOST_SUCCESS never calls the real tool
```

## 13. Definition of done for you

- [ ] `agent/plan.py` returns exactly 4 `StepContract`s in dependency order.
- [ ] Every tool in `agent/tools.py` is idempotent — calling
      `update_refund_db` twice with the same `refund_id` never crashes and
      never creates two rows.
- [ ] `FaultInjector` correctly produces each of GHOST_SUCCESS,
      TIMEOUT_THEN_RECOVER, WRONG_VALUE (COLLATERAL is stretch).
- [ ] `main.py` runs end-to-end with a real `DagRunner`/`IndependentVerifier`
      once Members 1 and 2 hand off their pieces (integration block, hour
      4:00–4:45 in the master plan).
- [ ] `render_metrics_table` prints real numbers from an actual run — not
      the 76%/0.8% numbers from the reference docs.

## 14. If you get stuck

Come back to this chat with: which member you are, the file you're editing,
the full error/traceback, and the current file content. Don't burn more
than ~10 minutes stuck alone — you don't have spare hours.
