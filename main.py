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
    rw.close()
    ro.close()
    if hasattr(ledger, "conn"):
        ledger.conn.close()
    return status, results

if __name__ == "__main__":
    build_fresh_world()
    status, results = run_veritas({"step_2": "COLLATERAL"})
    render_claim_vs_truth(results)
    render_final_banner(status)
    print(build_report(results, status))