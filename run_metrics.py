from db.connection import build_fresh_world, get_rw_conn, get_ro_conn
from agent.plan import DEMO_PLAN
from agent.executor import Executor
from harness.fault_injection import FaultInjector
from harness.baseline_agents import NaiveAgent, ground_truth_check
from harness.metrics import run_comparison
from dashboard.terminal_view import render_metrics_table

def run_naive(fault_map):
    rw = get_rw_conn()
    executor = Executor(rw, FaultInjector(fault_map))
    agent = NaiveAgent(executor)
    status, _ = agent.run(DEMO_PLAN)
    rw.close()
    ro = get_ro_conn()
    truth = ground_truth_check(ro)
    ro.close()
    return status, truth

def run_veritas_wrapper(fault_map):
    from main import run_veritas
    status, _ = run_veritas(fault_map)
    ro = get_ro_conn()
    truth = ground_truth_check(ro)
    ro.close()
    return status, truth

if __name__ == "__main__":
    rows, naive_rate, veritas_rate = run_comparison(build_fresh_world, run_naive, run_veritas_wrapper)
    render_metrics_table(rows, naive_rate, veritas_rate)