# ledger/evidence_ledger.py
import hashlib, json, sqlite3
from shared.contracts import Evidence, now, new_id

GENESIS_HASH = "0" * 64

class EvidenceLedger:
    def __init__(self, path="veritas_ledger.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("""CREATE TABLE IF NOT EXISTS evidence (
            evidence_id TEXT PRIMARY KEY,
            step_id TEXT, timestamp REAL, check_type TEXT,
            passed INTEGER, details TEXT, prev_hash TEXT, hash TEXT,
            trust_level TEXT NOT NULL DEFAULT 'HARD'
        )""")
        columns = {
            row[1] for row in self.conn.execute("PRAGMA table_info(evidence)")
        }
        if "trust_level" not in columns:
            self.conn.execute(
                "ALTER TABLE evidence ADD COLUMN trust_level TEXT NOT NULL DEFAULT 'HARD'"
            )
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
            "trust_level": "HARD",
        }
        record_hash = hashlib.sha256(
            (prev_hash + json.dumps(payload, sort_keys=True)).encode()
        ).hexdigest()
        ev = Evidence(
            evidence_id=new_id("EVD"), step_id=step_id, timestamp=now(),
            check_type=check_type, passed=passed, details=details,
            prev_hash=prev_hash, hash=record_hash,
            trust_level="HARD",
        )
        self.conn.execute(
            "INSERT INTO evidence VALUES (?,?,?,?,?,?,?,?,?)",
            (ev.evidence_id, ev.step_id, ev.timestamp, ev.check_type,
             int(ev.passed), json.dumps(ev.details), ev.prev_hash, ev.hash,
             ev.trust_level),
        )
        self.conn.commit()
        return ev

    def verify_chain(self) -> list[tuple[str, str]]:
        """Return the integrity status of every evidence record."""
        rows = self.conn.execute(
            "SELECT evidence_id, step_id, check_type, passed, details, "
            "prev_hash, hash, trust_level "
            "FROM evidence ORDER BY rowid ASC"
        ).fetchall()
        expected_prev = GENESIS_HASH
        statuses = []
        for evidence_id, step_id, check_type, passed, details, prev_hash, hash_, trust_level in rows:
            valid = prev_hash == expected_prev
            payload = {
                "step_id": step_id, "check_type": check_type,
                "passed": bool(passed), "details": json.loads(details),
                "prev_hash": prev_hash,
                "trust_level": trust_level,
            }
            recomputed = hashlib.sha256(
                (prev_hash + json.dumps(payload, sort_keys=True)).encode()
            ).hexdigest()
            valid = valid and recomputed == hash_
            statuses.append((evidence_id, "VERIFIED" if valid else "UNVERIFIABLE"))
            expected_prev = hash_
        return statuses

    def verify_chain_bool(self) -> bool:
        return all(status == "VERIFIED" for _, status in self.verify_chain())

    def export_proof_bundle(self, out_path):
        return export_proof_bundle(self, out_path)


def export_proof_bundle(ledger, out_path):
    rows = ledger.conn.execute(
        "SELECT evidence_id, step_id, timestamp, check_type, passed, details, "
        "prev_hash, hash, trust_level FROM evidence ORDER BY rowid ASC"
    ).fetchall()
    evidence = [
        {
            "evidence_id": row[0],
            "step_id": row[1],
            "timestamp": row[2],
            "check_type": row[3],
            "passed": bool(row[4]),
            "details": json.loads(row[5]),
            "prev_hash": row[6],
            "hash": row[7],
            "trust_level": row[8],
        }
        for row in rows
    ]
    array_json = json.dumps(evidence, sort_keys=True, separators=(",", ":"))
    bundle = {
        "evidence": evidence,
        "bundle_hash": hashlib.sha256(array_json.encode()).hexdigest(),
    }
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(bundle, handle, sort_keys=True, separators=(",", ":"))
    return out_path