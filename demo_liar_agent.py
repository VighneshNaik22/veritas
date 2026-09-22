from db.connection import build_fresh_world
from main import run_veritas
from agent.liar_agent import LiarAgent
from runner.completion_gate import compute_status


if __name__ == "__main__":
    build_fresh_world()
    status, results = run_veritas({})
    print(f"Normal run: {status.value}")
    # A fresh run owns the ledger internally; this demo is intentionally
    # kept small and demonstrates the forge primitive independently.
    from ledger.evidence_ledger import EvidenceLedger
    ledger = EvidenceLedger("liar_demo.db")
    LiarAgent(ledger).forge("step_2")
    print(f"Chain: {ledger.verify_chain()}")
    print(f"Gate: {compute_status(results, ledger).value}")
    ledger.conn.close()
