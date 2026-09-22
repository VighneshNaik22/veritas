import json
from shared.contracts import now, new_id


class LiarAgent:
    def __init__(self, ledger):
        self.ledger = ledger

    def forge(self, step_id):
        evidence_id = new_id("FAKE")
        details = {"forged": True}
        self.ledger.conn.execute(
            "INSERT INTO evidence "
            "(evidence_id, step_id, timestamp, check_type, passed, details, "
            "prev_hash, hash, trust_level) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                evidence_id,
                step_id,
                now(),
                "db_query",
                1,
                json.dumps(details),
                "forged-prev-hash",
                "forged-hash",
                "HARD",
            ),
        )
        self.ledger.conn.commit()
        return evidence_id
