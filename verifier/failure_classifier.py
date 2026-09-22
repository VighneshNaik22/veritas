# verifier/failure_classifier.py
from shared.contracts import FailureClass

def classify(contract, state: dict, passed: bool,
             raised_timeout: bool = False,
             collateral_detected: bool = False) -> FailureClass:
    if raised_timeout:
        return FailureClass.TIMEOUT
    if collateral_detected:
        return FailureClass.COLLATERAL
    if passed:
        return FailureClass.NONE

    if contract.tool == "update_refund_db":
        rows = state.get("rows", [])
        if len(rows) == 0:
            return FailureClass.NO_EFFECT
        if len(rows) > 1:
            return FailureClass.DUPLICATE
        row = rows[0]
        if row["status"] != contract.expected.get("status"):
            return FailureClass.PARTIAL
        if row["amount"] != contract.expected.get("amount"):
            return FailureClass.WRONG_VALUE
        return FailureClass.PARTIAL

    if state.get("row_count", 0) == 0:
        return FailureClass.NO_EFFECT
    return FailureClass.PARTIAL