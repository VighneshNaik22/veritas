from shared.contracts import RunStatus

class NaiveAgent:
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