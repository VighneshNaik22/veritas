import datetime
from shared.contracts import new_id

def check_eligibility(rw_conn, args):
    row = rw_conn.execute("SELECT eligible FROM customers WHERE customer_id=?",
                           (args["customer_id"],)).fetchone()
    return {"status": "success" if row else "not_found"}

def update_refund_db(rw_conn, args):
    existing = rw_conn.execute(
        "SELECT 1 FROM refunds WHERE refund_id=?", (args["refund_id"],)
    ).fetchone()
    if existing:
        rw_conn.execute(
            "UPDATE refunds SET amount=?, status=?, idempotency_key=? WHERE refund_id=?",
            (args["amount"], "processed", args.get("idempotency_key"), args["refund_id"]),
        )
    else:
        rw_conn.execute(
            "INSERT INTO refunds (refund_id, customer_id, amount, status, idempotency_key) "
            "VALUES (?,?,?,?,?)",
            (args["refund_id"], args["customer_id"], args["amount"], "processed",
             args.get("idempotency_key")),
        )
    rw_conn.commit()
    return {"status": "success"}

def send_confirmation_email(rw_conn, args):
    rw_conn.execute(
        "INSERT INTO sent_emails (email_id, customer_id, refund_id, subject, sent_at) "
        "VALUES (?,?,?,?,?)",
        (new_id("MAIL"), args["customer_id"], args["refund_id"], "Your refund is processed",
         datetime.datetime.utcnow().isoformat()),
    )
    rw_conn.commit()
    return {"status": "success"}

def log_audit(rw_conn, args):
    rw_conn.execute(
        "INSERT INTO audit_log (log_id, step_id, message, logged_at) VALUES (?,?,?,?)",
        (new_id("LOG"), args["step_id"], args["message"], datetime.datetime.utcnow().isoformat()),
    )
    rw_conn.commit()
    return {"status": "success"}

TOOL_REGISTRY = {
    "check_eligibility": check_eligibility,
    "update_refund_db": update_refund_db,
    "send_confirmation_email": send_confirmation_email,
    "log_audit": log_audit,
}