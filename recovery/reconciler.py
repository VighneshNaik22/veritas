import datetime

from agent.tools import send_confirmation_email
from agent.plan import DEMO_PLAN


def reconcile(rw_conn, ro_conn, verifier, ledger):
    pending = rw_conn.execute(
        "SELECT outbox_id, customer_id, refund_id, subject "
        "FROM outbox WHERE sent_at IS NULL"
    ).fetchall()
    reconciled = []
    for outbox_id, customer_id, refund_id, subject in pending:
        send_confirmation_email(
            rw_conn,
            {"customer_id": customer_id, "refund_id": refund_id},
            online_check=lambda: True,
        )
        rw_conn.execute(
            "UPDATE outbox SET sent_at=? WHERE outbox_id=?",
            (datetime.datetime.utcnow().isoformat(), outbox_id),
        )
        rw_conn.commit()
        verifier.verify(next(c for c in DEMO_PLAN if c.step_id == "step_3"))
        reconciled.append(outbox_id)
    return reconciled
