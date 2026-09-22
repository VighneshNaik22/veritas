# ledger/evidence_ledger.py
import hashlib, json, sqlite3
from shared.contracts import Evidence, now, new_id

GENESIS_HASH = "0" * 64

class EvidenceLedger:
    def __init__(self, path="veritas_ledger.db"):
        self.conn = sqlite3.connect(path)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS evidence (
            evidence_id TEXT PRIMARY KEY,
            step_id TEXT, timestamp REAL, check_type TEXT,
            passed INTEGER, details TEXT, prev_hash TEXT, hash TEXT
        )""")
        self.conn.commit()

    def _last_hash(self) -> str:
        row = self.conn.execute(
            "SELECT hash FROM evidence ORDER BY rowid DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else GENESIS_HASH

    def add(self, step_id, check_type, passed, details) -> Evidence:
        prev_hash = self._last_hash()
        payload = {
            "step_id": step_id, "check_type": check_type,
            "passed": passed, "details": details, "prev_hash": prev_hash,
        }
        record_hash = hashlib.sha256(
            (prev_hash + json.dumps(payload, sort_keys=True)).encode()
        ).hexdigest()
        ev = Evidence(
            evidence_id=new_id("EVD"), step_id=step_id, timestamp=now(),
            check_type=check_type, passed=passed, details=details,
            prev_hash=prev_hash, hash=record_hash,
        )
        self.conn.execute(
            "INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?)",
            (ev.evidence_id, ev.step_id, ev.timestamp, ev.check_type,
             int(ev.passed), json.dumps(ev.details), ev.prev_hash, ev.hash),
        )
        self.conn.commit()
        return ev

    def verify_chain(self) -> bool:
        """Walk every record, recompute hashes. False if anything was
        edited or deleted out of band."""
        rows = self.conn.execute(
            "SELECT step_id, check_type, passed, details, prev_hash, hash "
            "FROM evidence ORDER BY rowid ASC"
        ).fetchall()
        expected_prev = GENESIS_HASH
        for step_id, check_type, passed, details, prev_hash, hash_ in rows:
            if prev_hash != expected_prev:
                return False
            payload = {
                "step_id": step_id, "check_type": check_type,
                "passed": bool(passed), "details": json.loads(details),
                "prev_hash": prev_hash,
            }
            recomputed = hashlib.sha256(
                (prev_hash + json.dumps(payload, sort_keys=True)).encode()
            ).hexdigest()
            if recomputed != hash_:
                return False
            expected_prev = hash_
        return True