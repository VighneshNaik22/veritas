# verifier/independent_verifier.py
from shared.contracts import Evidence
from verifier.checker import read_state
from ledger.evidence_ledger import EvidenceLedger

class IndependentVerifier:
    def __init__(self, ro_conn, ledger: EvidenceLedger):
        self.ro_conn = ro_conn      # opened mode=ro -- physically cannot write
        self.ledger = ledger

    def verify(self, contract) -> Evidence:
        state = read_state(self.ro_conn, contract)
        passed = self._matches_expected(contract, state)
        return self.ledger.add(
            step_id=contract.step_id, check_type="db_query",
            passed=passed, details=state,
        )

    def snapshot(self) -> dict:
        """Used only for the COLLATERAL stretch check (see below)."""
        customers = dict(self.ro_conn.execute(
            "SELECT customer_id, eligible FROM customers").fetchall())
        return {"customers": customers}

    def collateral_detected(self, before: dict, contract) -> bool:
        """Stretch goal -- build this LAST, after everything else works.
        Detects damage outside a step's declared write-set."""
        if contract.tool != "update_refund_db":
            return False
        after = dict(self.ro_conn.execute(
            "SELECT customer_id, eligible FROM customers").fetchall())
        touched = contract.args.get("customer_id")
        for cust_id, elig in after.items():
            if cust_id == touched:
                continue
            if before["customers"].get(cust_id) != elig:
                return True
        return False

    @staticmethod
    def _matches_expected(contract, state: dict) -> bool:
        if contract.tool == "check_eligibility":
            return state.get("eligible") == contract.expected.get("eligible")
        if contract.tool == "update_refund_db":
            rows = state.get("rows", [])
            if not rows:
                return False
            row = rows[0]
            return (row["amount"] == contract.expected.get("amount")
                    and row["status"] == contract.expected.get("status"))
        if contract.tool in ("send_confirmation_email", "log_audit"):
            return state.get("row_count", 0) >= 1
        return False