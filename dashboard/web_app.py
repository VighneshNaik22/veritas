import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from db.connection import build_fresh_world, get_ro_conn
from dashboard.auth import SESSION_TTL_SECONDS, request_otp, verify_otp
from main import run_veritas
from shared.contracts import RunStatus

logger = logging.getLogger("veritas.dashboard")

HOST = os.environ.get("VERITAS_HOST", "0.0.0.0")
PORT = int(os.environ.get("VERITAS_PORT", "8000"))
ROOT = Path(__file__).resolve().parent.parent
_lock = threading.Lock()
_last_run = None
_sessions = {}
_session_lock = threading.Lock()

FAULTS = {
    "CLEAN": {},
    "GHOST_SUCCESS": {"step_2": "GHOST_SUCCESS"},
    "TIMEOUT_THEN_RECOVER": {"step_2": "TIMEOUT_THEN_RECOVER"},
    "WRONG_VALUE": {"step_2": "WRONG_VALUE"},
    "COLLATERAL": {"step_2": "COLLATERAL"},
}


def _json_value(value):
    if hasattr(value, "value"):
        return value.value
    return value


def _read_rows(conn, query, args=()):
    cursor = conn.execute(query, args)
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _state():
    ro = get_ro_conn()
    try:
        ledger = getattr(run_veritas, "last_ledger", None)
        evidence_count = 0
        chain = []
        if ledger is not None:
            evidence_count = ledger.conn.execute(
                "SELECT COUNT(*) FROM evidence"
            ).fetchone()[0]
            chain = ledger.verify_chain()

        steps = []
        if _last_run is not None:
            for step_id, result in _last_run["results"].items():
                evidence = result.evidence
                steps.append({
                    "step_id": step_id,
                    "status": _json_value(result.status),
                    "claim": result.claim,
                    "failure_class": _json_value(result.failure_class),
                    "attempts": result.attempts,
                    "escalated": result.escalated,
                    "evidence": {
                        "passed": evidence.passed,
                        "details": evidence.details,
                        "trust_level": evidence.trust_level,
                        "evidence_id": evidence.evidence_id,
                    } if evidence else None,
                })

        return {
            "run_status": _last_run["status"] if _last_run else "NOT_RUN",
            "fault_mode": _last_run["fault_mode"] if _last_run else None,
            "steps": steps,
            "ledger": {
                "evidence_count": evidence_count,
                "chain_status": (
                    "VERIFIED"
                    if all(status == "VERIFIED" for _, status in chain)
                    else "TAMPERED"
                ),
                "records": [
                    {"evidence_id": evidence_id, "status": status}
                    for evidence_id, status in chain
                ],
            },
            "preflight": "PASSED" if _last_run else "NOT_RUN",
            "tables": {
                "refunds": _read_rows(
                    ro, "SELECT refund_id, customer_id, amount, status FROM refunds"
                ),
                "emails": _read_rows(
                    ro,
                    "SELECT email_id, refund_id, subject, sent_at "
                    "FROM sent_emails ORDER BY rowid DESC",
                ),
                "outbox": _read_rows(
                    ro,
                    "SELECT outbox_id, refund_id, queued_at, sent_at "
                    "FROM outbox ORDER BY rowid DESC",
                ),
            },
        }
    finally:
        ro.close()


def _run(fault_mode):
    global _last_run
    with _lock:
        build_fresh_world()
        status, results = run_veritas(FAULTS[fault_mode])
        _last_run = {
            "status": status.value,
            "fault_mode": fault_mode,
            "results": results,
        }
        return _state()


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VERITAS / Trust Console</title>
<style>
:root { --bg:#08111f; --panel:#101d30; --line:#223451; --muted:#8da1bd;
  --text:#edf4ff; --cyan:#57d5e8; --green:#53d49a; --amber:#f3bd62;
  --red:#ff737d; --purple:#b493ff; }
* { box-sizing:border-box; } body { margin:0; background:radial-gradient(circle at 80% -10%,#17345c 0,#08111f 42%);
  color:var(--text); font:14px/1.5 Inter,ui-sans-serif,system-ui,sans-serif; }
main { max-width:1280px; margin:0 auto; padding:34px 24px 60px; }
.eyebrow { color:var(--cyan); font-weight:700; letter-spacing:.16em; font-size:11px; }
h1 { font-size:36px; letter-spacing:-.04em; margin:7px 0 6px; } h2 { font-size:16px; margin:0 0 16px; }
.subtitle { color:var(--muted); margin:0 0 28px; max-width:680px; }
.toolbar { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:22px; }
select,button { border:1px solid var(--line); border-radius:8px; padding:10px 13px; background:#13243b; color:var(--text); font:inherit; }
button { background:var(--cyan); color:#06131f; border:0; font-weight:800; cursor:pointer; } button:disabled { opacity:.55; cursor:wait; }
.grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:18px; }
.card,.panel { background:rgba(16,29,48,.88); border:1px solid var(--line); border-radius:13px; }
.card { padding:17px; min-height:105px; } .label { color:var(--muted); font-size:12px; } .value { font-size:25px; font-weight:800; margin-top:10px; }
.panel { padding:20px; margin-bottom:18px; } .panel-head { display:flex; justify-content:space-between; align-items:center; gap:10px; }
.pill { display:inline-flex; border-radius:999px; padding:4px 9px; font-size:11px; font-weight:800; letter-spacing:.04em; }
.VERIFIED,.COMPLETE { color:var(--green); background:#123d35; } .FAILED,.ESCALATED { color:var(--red); background:#48232e; }
.BLOCKED,.PARTIAL { color:var(--amber); background:#47361c; } .STALE { color:var(--purple); background:#30254c; }
.NOT_RUN { color:var(--muted); background:#223047; } .QUEUED { color:var(--cyan); background:#123c49; }
table { width:100%; border-collapse:collapse; } th { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; text-align:left; }
th,td { padding:12px 8px; border-bottom:1px solid #1e3049; vertical-align:top; } td { color:#dce8f7; }
code { color:var(--cyan); font-size:12px; } .muted { color:var(--muted); } .two { display:grid; grid-template-columns:1fr 1fr; gap:18px; }
.empty { color:var(--muted); padding:8px 0; } .notice { color:var(--muted); margin-top:10px; min-height:20px; }
@media (max-width:850px) { .grid { grid-template-columns:repeat(2,1fr); } .two { grid-template-columns:1fr; } }
@media (max-width:520px) { main { padding:24px 14px; } h1 { font-size:29px; } .grid { grid-template-columns:1fr 1fr; } }
</style>
</head>
<body><main>
<div class="eyebrow">ZERO-TRUST WORKFLOW OBSERVABILITY</div>
<h1>VERITAS / Trust Console</h1>
<p class="subtitle">A live view of what the agent claimed, what independent verification found,
and whether the evidence is strong enough to complete the workflow.</p>
<div class="toolbar">
  <select id="mode"><option>CLEAN</option><option>GHOST_SUCCESS</option>
    <option>TIMEOUT_THEN_RECOVER</option><option>WRONG_VALUE</option><option>COLLATERAL</option></select>
  <button id="run">Run workflow</button><span class="notice" id="notice"></span>
</div>
<section class="grid">
  <div class="card"><div class="label">RUN STATUS</div><div class="value" id="run-status">—</div></div>
  <div class="card"><div class="label">EVIDENCE RECORDS</div><div class="value" id="evidence-count">—</div></div>
  <div class="card"><div class="label">LEDGER INTEGRITY</div><div class="value" id="ledger-status">—</div></div>
  <div class="card"><div class="label">PREFLIGHT</div><div class="value" id="preflight">—</div></div>
</section>
<section class="panel"><div class="panel-head"><h2>Workflow truth table</h2><span class="muted" id="mode-label"></span></div>
<table><thead><tr><th>Step</th><th>Claim</th><th>Verified truth</th><th>Status</th><th>Attempts</th></tr></thead>
<tbody id="steps"></tbody></table></section>
<div class="two">
<section class="panel"><h2>Evidence chain</h2><table><thead><tr><th>Evidence ID</th><th>Integrity</th></tr></thead><tbody id="evidence"></tbody></table></section>
<section class="panel"><h2>Persisted business state</h2><table><thead><tr><th>Refund</th><th>Emails</th><th>Outbox</th></tr></thead><tbody id="business"></tbody></table></section>
</div>
</main>
<script>
const $ = id => document.getElementById(id);
function pill(text) { const cls = text === 'QUEUED (offline)' ? 'QUEUED' : text; return `<span class="pill ${cls}">${text}</span>`; }
function render(data) {
  $('run-status').innerHTML = pill(data.run_status); $('evidence-count').textContent = data.ledger.evidence_count;
  $('ledger-status').innerHTML = pill(data.ledger.chain_status); $('preflight').innerHTML = pill(data.preflight);
  $('mode-label').textContent = data.fault_mode ? `scenario: ${data.fault_mode}` : '';
  $('steps').innerHTML = data.steps.length ? data.steps.map(s => {
    const queued = s.claim && s.claim.toLowerCase().includes('queued_offline');
    const status = queued ? 'QUEUED (offline)' : s.status;
    const truth = s.evidence ? (s.evidence.passed ? 'Matches observed state' : 'Does not match observed state') : 'No verification record';
    return `<tr><td><code>${s.step_id}</code></td><td>${s.claim || '<span class="muted">—</span>'}</td><td>${truth}</td><td>${pill(status)}</td><td>${s.attempts || '—'}</td></tr>`;
  }).join('') : '<tr><td colspan="5" class="empty">Run a scenario to inspect the workflow.</td></tr>';
  $('evidence').innerHTML = data.ledger.records.length ? data.ledger.records.map(e => `<tr><td><code>${e.evidence_id}</code></td><td>${pill(e.status)}</td></tr>`).join('') : '<tr><td colspan="2" class="empty">No evidence yet.</td></tr>';
  const r = data.tables.refunds.map(x => `${x.refund_id} · $${x.amount} · ${x.status}`).join('<br>') || '—';
  const e = data.tables.emails.map(x => `${x.refund_id} · ${x.sent_at}`).join('<br>') || '—';
  const o = data.tables.outbox.map(x => `${x.refund_id} · ${x.sent_at ? 'sent' : 'pending'}`).join('<br>') || '—';
  $('business').innerHTML = `<tr><td>${r}</td><td>${e}</td><td>${o}</td></tr>`;
}
async function refresh() { const response = await fetch('/api/state'); render(await response.json()); }
$('run').onclick = async () => { $('run').disabled = true; $('notice').textContent = 'Running real workflow…'; try {
  const response = await fetch('/api/run', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({mode:$('mode').value})});
  const data = await response.json(); render(data); $('notice').textContent = 'Run complete — data read from SQLite and the evidence ledger.';
} catch (e) { $('notice').textContent = e.message; } finally { $('run').disabled = false; } };
refresh();
</script>
</body></html>"""

LOGIN_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>VERITAS / Login</title><style>
body{margin:0;background:#08111f;color:#edf4ff;font:15px system-ui,sans-serif;display:grid;place-items:center;min-height:100vh}
main{width:min(420px,calc(100% - 36px));background:#101d30;border:1px solid #223451;border-radius:14px;padding:30px}
h1{margin:8px 0}.muted{color:#8da1bd}.eyebrow{color:#57d5e8;font-size:11px;font-weight:700;letter-spacing:.15em}
label{display:block;margin-top:20px;color:#8da1bd}input,button{width:100%;box-sizing:border-box;border:1px solid #2b4262;border-radius:8px;padding:12px;margin-top:7px;background:#13243b;color:#edf4ff;font:inherit}
button{background:#57d5e8;color:#06131f;border:0;font-weight:800;cursor:pointer}.hidden{display:none}.message{min-height:22px;color:#f3bd62;margin-top:14px}
</style></head><body><main><div class="eyebrow">ZERO-TRUST WORKFLOW OBSERVABILITY</div>
<h1>Sign in to VERITAS</h1><p class="muted">Use your registered email. We will send a one-time code.</p>
<form id="request"><label>Email<input id="email" type="email" required autocomplete="email"></label>
<button type="submit">Send login code</button></form>
<form id="verify" class="hidden"><label>One-time code<input id="otp" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required autocomplete="one-time-code"></label>
<button type="submit">Verify and continue</button></form><div id="message" class="message"></div>
<script>
const requestForm=document.getElementById('request'), verifyForm=document.getElementById('verify'), message=document.getElementById('message');
requestForm.onsubmit=async e=>{e.preventDefault();const r=await fetch('/auth/request-otp',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:document.getElementById('email').value})});const d=await r.json();message.textContent=d.message;if(r.ok){verifyForm.classList.remove('hidden');}};
verifyForm.onsubmit=async e=>{e.preventDefault();const r=await fetch('/auth/verify',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:document.getElementById('email').value,otp:document.getElementById('otp').value})});const d=await r.json();if(r.ok){location.href='/';}else{message.textContent=d.message;}};
</script></main></body></html>"""


def _session_user(handler):
    raw = handler.headers.get("Cookie", "")
    token = next(
        (part.strip().split("=", 1)[1] for part in raw.split(";")
         if part.strip().startswith("veritas_session=")),
        None,
    )
    if not token:
        return None
    with _session_lock:
        created = _sessions.get(token)
        if created is None:
            return None
        if time.time() - created > SESSION_TTL_SECONDS:
            _sessions.pop(token, None)
            return None
    return token


class Handler(BaseHTTPRequestHandler):
    def _send(self, body, content_type, status=200):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/login":
            self._send(LOGIN_PAGE, "text/html; charset=utf-8")
        elif path == "/logout":
            token = _session_user(self)
            if token:
                with _session_lock:
                    _sessions.pop(token, None)
            self.send_response(302)
            self.send_header("Set-Cookie", "veritas_session=; Max-Age=0; HttpOnly; SameSite=Lax; Path=/")
            self.send_header("Location", "/login")
            self.end_headers()
        elif path == "/api/state" and _session_user(self):
            self._send(json.dumps(_state()), "application/json")
        elif path == "/" and _session_user(self):
            self._send(PAGE, "text/html; charset=utf-8")
        elif path.startswith("/api/"):
            self._send(json.dumps({"message": "Login required."}), "application/json", 401)
        elif path == "/":
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()
        else:
            self._send("Not found", "text/plain", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/auth/request-otp":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                email = payload.get("email", "")
                if not isinstance(email, str) or "@" not in email:
                    self._send(json.dumps({"message": "Enter a valid email address."}), "application/json", 400)
                    return
                _, message = request_otp(email, self.client_address[0])
                self._send(json.dumps({"message": message}), "application/json")
            except (ValueError, json.JSONDecodeError):
                self._send(json.dumps({"message": "Invalid request."}), "application/json", 400)
            return
        if path == "/auth/verify":
            try:
                length = int(self.headers.get("Content-Length", "0"))
                payload = json.loads(self.rfile.read(length) or b"{}")
                token, message = verify_otp(
                    payload.get("email", ""),
                    payload.get("otp", ""),
                    self.client_address[0],
                )
                if not token:
                    self._send(json.dumps({"message": message}), "application/json", 401)
                    return
                with _session_lock:
                    _sessions[token] = time.time()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Set-Cookie", "veritas_session=" + token + "; HttpOnly; SameSite=Lax; Path=/")
                body = json.dumps({"message": "Authenticated."}).encode()
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (ValueError, json.JSONDecodeError):
                self._send(json.dumps({"message": "Invalid request."}), "application/json", 400)
            return
        if path != "/api/run":
            self._send("Not found", "text/plain", 404)
            return
        if not _session_user(self):
            self._send(json.dumps({"message": "Login required."}), "application/json", 401)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
            mode = payload.get("mode", "CLEAN")
            if mode not in FAULTS:
                raise ValueError(f"Unknown scenario: {mode}")
            self._send(json.dumps(_run(mode)), "application/json")
        except (ValueError, json.JSONDecodeError) as error:
            self._send(json.dumps({"error": str(error)}), "application/json", 400)

    def log_message(self, format, *args):
        return


def create_server(host=HOST, port=PORT):
    build_fresh_world()
    return ThreadingHTTPServer((host, port), Handler)


def serve(host=HOST, port=PORT):
    server = create_server(host, port)
    print(f"VERITAS dashboard: http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
