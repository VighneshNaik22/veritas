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
        expected={"row_count": 1}, idempotency_key="email-R123",
        reversible=False,
    ),
    StepContract(
        step_id="step_4", name="log_audit", depends_on=["step_3"],
        tool="log_audit",
        args={"step_id": "refund_flow", "message": "refund R123 processed and emailed"},
        expected={"row_count": 1}, idempotency_key="audit-refund_flow",
    ),
]