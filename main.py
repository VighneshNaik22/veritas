import sys

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
from preflight.checker import check_plan
from dashboard.terminal_view import (
    render_claim_vs_truth,
    render_final_banner,
    render_ledger_summary,
)
from harness import network_status
from recovery.reconciler import reconcile
from recovery.reconnect_watcher import ReconnectWatcher

def run_veritas(fault_map):
    previous_ledger = getattr(run_veritas, "last_ledger", None)
    if previous_ledger is not None:
        previous_ledger.conn.close()
    rw = get_rw_conn()
    ro = get_ro_conn()
    ledger = EvidenceLedger()
    executor = Executor(rw, FaultInjector(fault_map))
    verifier = IndependentVerifier(ro, ledger)
    runner = DagRunner(executor, verifier, classify, recovery_engine)
    violations = check_plan(DEMO_PLAN)
    if violations:
        rw.close()
        ro.close()
        raise RuntimeError("Plan preflight failed:\n" + "\n".join(violations))
    results = runner.run(DEMO_PLAN)
    status = compute_status(results)
    rw.close()
    ro.close()
    run_veritas.last_ledger = ledger
    return status, results


def run_offline_recovery_demo():
    build_fresh_world()
    rw = get_rw_conn()
    ro = get_ro_conn()
    ledger = EvidenceLedger()
    verifier = IndependentVerifier(ro, ledger)
    runner = DagRunner(
        Executor(rw, FaultInjector()),
        verifier,
        classify,
        recovery_engine,
    )
    watcher = ReconnectWatcher(
        rw, ro, verifier, ledger, reconcile, interval=1.0
    )
    watcher.start()
    network_status.FORCE_OFFLINE = True
    print("OFFLINE START; FORCE_OFFLINE=True")
    offline_results = runner.run(DEMO_PLAN)
    print("OFFLINE RUN")
    render_claim_vs_truth(offline_results)
    render_final_banner(compute_status(offline_results))

    print("WAITING DURING OUTAGE...")
    import time
    time.sleep(3)
    network_status.FORCE_OFFLINE = False
    print("FORCE_OFFLINE=False; waiting for reconnect watcher")
    if not watcher.wait_for_reconciliation(timeout=10):
        watcher.stop()
        raise RuntimeError("Reconnect watcher did not reconcile in time")
    recovered_results = runner.run(DEMO_PLAN)
    watcher.stop()
    render_claim_vs_truth(recovered_results)
    render_final_banner(compute_status(recovered_results))
    render_ledger_summary(ledger)
    rw.close()
    ro.close()
    ledger.conn.close()

if __name__ == "__main__" and "--offline-demo" in sys.argv:
    run_offline_recovery_demo()
elif __name__ == "__main__":
    build_fresh_world()
    status, results = run_veritas({"step_2": "COLLATERAL"})
    render_claim_vs_truth(results)
    render_final_banner(status)
    render_ledger_summary(run_veritas.last_ledger)
    print(build_report(results, status))
    run_veritas.last_ledger.conn.close()