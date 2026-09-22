import sqlite3, os, pathlib

DB_PATH = "veritas.db"
LEDGER_PATH = "veritas_ledger.db"
SCHEMA_PATH = pathlib.Path(__file__).parent / "schema.sql"

def build_fresh_world():
    for path in (DB_PATH, LEDGER_PATH):
        if os.path.exists(path):
            os.remove(path)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA_PATH.read_text())
    conn.commit()
    conn.close()

def get_rw_conn():
    return sqlite3.connect(DB_PATH)

def get_ro_conn():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)