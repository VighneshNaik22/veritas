# verifier/checker.py

def read_state(ro_conn, contract) -> dict:
    tool = contract.tool
    args = contract.args

    if tool == "check_eligibility":
        row = ro_conn.execute(
            "SELECT eligible FROM customers WHERE customer_id=?",
            (args["customer_id"],),
        ).fetchone()
        return {"eligible": row[0] if row else None}

    if tool == "update_refund_db":
        rows = ro_conn.execute(
            "SELECT refund_id, amount, status FROM refunds WHERE refund_id=?",
            (args["refund_id"],),
        ).fetchall()
        return {"row_count": len(rows),
                "rows": [{"refund_id": r[0], "amount": r[1], "status": r[2]} for r in rows]}

    if tool == "send_confirmation_email":
        rows = ro_conn.execute(
            "SELECT email_id FROM sent_emails WHERE refund_id=?",
            (args["refund_id"],),
        ).fetchall()
        return {"row_count": len(rows)}

    if tool == "log_audit":
        rows = ro_conn.execute(
            "SELECT log_id FROM audit_log WHERE step_id=?",
            (args["step_id"],),
        ).fetchall()
        return {"row_count": len(rows)}

    raise ValueError(f"No checker registered for tool '{tool}'")