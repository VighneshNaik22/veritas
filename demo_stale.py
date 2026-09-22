import sqlite3

from agent.executor import Executor
from agent.plan import DEMO_PLAN
from db.connection import build_fresh_world, get_ro_conn, get_rw_conn
from harness.fault_injection import FaultInjector
from ledger.evidence_ledger import EvidenceLedger
from recovery import recovery_engine
from runner.completion_gate import compute_status
from runner.dag_runner import DagRunner
from verifier.failure_classifier import classify
from verifier.independent_verifier import IndependentVerifier


if __name__ == "__main__":
    build_fresh_world()
    rw = get_rw_conn()
    ro = get_ro_conn()
    ledger = EvidenceLedger("stale_demo.db")
    runner = DagRunner(
        Executor(rw, FaultInjector()),
        IndependentVerifier(ro, ledger),
        classify,
        recovery_engine,
    )
    results = runner.run(DEMO_PLAN)
    print(f"Initial: {compute_status(results).value}")
    rw.execute("UPDATE refunds SET amount=1 WHERE refund_id='R123'")
    rw.commit()
    print(f"Marked stale: {runner.mark_stale('step_2', results)}")
    print(f"After mutation: {compute_status(results).value}")
    results = runner.run(DEMO_PLAN)
    print(f"After re-verification: {compute_status(results).value}")
    rw.close()
    ro.close()
    ledger.conn.close()
