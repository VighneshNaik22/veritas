# VERITAS — Evidence-Gated Self-Healing Agent Workflow

VERITAS is a zero-trust refund-processing prototype. It never treats an
agent's success message as proof. Every step is independently checked against
the real database before it can be marked `VERIFIED`.

The project includes:

- Dependency-aware refund execution
- Independent read-only verification
- Fault injection and failure classification
- Retry, escalation, and completion gating
- Offline local processing with an outbox
- Automatic reconnect detection and reconciliation
- Tamper-evident, hash-chained evidence
- Proof-bundle verification
- Stale-data detection
- Forged-evidence/LiarAgent demonstrations
- Preflight safety checks
- Terminal and web dashboards
- OTP-protected dashboard login with SMTP delivery

## Quick start

Install the runtime dependency and run the default workflow:

```bash
pip install -r requirements.txt
python main.py
```

The default run creates a fresh SQLite world, checks the plan, executes the
refund workflow, independently verifies each step, and renders the claims
versus truth, final status, evidence count, and ledger integrity.

## Web dashboard

Start the dashboard with:

```bash
python run_dashboard.py
```

Open `http://localhost:8000`, or open the forwarded port 8000 URL in
Codespaces. The server binds to `0.0.0.0` by default so forwarded ports can
reach it. Optional overrides are:

```bash
export VERITAS_HOST=0.0.0.0
export VERITAS_PORT=8000
```

The dashboard uses real SQLite data and displays:

- Workflow and per-step status
- Agent claims versus independently verified truth
- Evidence records and hash-chain integrity
- Preflight state
- Refund, sent-email, and offline-outbox records
- Clean and fault-injected scenarios

## Dashboard OTP login

Unauthenticated dashboard requests redirect to the login page. The login flow
is:

```text
Enter email → receive one-time code → verify code → receive session → dashboard
```

### Development mode

Development mode is enabled by default when no explicit setting is provided.
It does not send real email; it prints a development-only OTP in the server
terminal:

```bash
export VERITAS_AUTH_DEV_MODE=1
python run_dashboard.py
```

The terminal output contains a line like:

```text
DEV ONLY OTP for user@example.com: 371093
```

### Real SMTP mode

For Gmail, create an App Password and configure the sender through environment
variables. Never commit the password:

```bash
export VERITAS_AUTH_DEV_MODE=0
export VERITAS_SMTP_HOST=smtp.gmail.com
export VERITAS_SMTP_PORT=587
export VERITAS_SMTP_USER='your-gmail@gmail.com'
export VERITAS_SMTP_PASSWORD='your-16-character-app-password'
export VERITAS_SMTP_FROM='your-gmail@gmail.com'
export VERITAS_OTP_PEPPER='a-long-random-secret'
python run_dashboard.py
```

`VERITAS_SMTP_FROM` defaults to `VERITAS_SMTP_USER`. The OTP is sent to the
exact normalized email address submitted in that login request, not to a fixed
demo address.

OTP security behavior:
- Six-digit random code
- Five-minute expiration
- Single-use challenge
- At most five verification attempts per challenge
- At most three requests per IP in fifteen minutes
- Only an HMAC-SHA256 hash is stored in SQLite
- Generic browser response to avoid email-existence leaks
- Session required for protected dashboard routes

## Offline and automatic reconnect demo

Run the complete disconnect → operate → reconnect → recover flow:

```bash
python main.py --offline-demo
```

The demo:

1. Starts the reconnect watcher.
2. Forces connectivity offline.
3. Performs real local database work for eligibility and refund processing.
4. Queues the confirmation email in the SQLite `outbox` table.
5. Displays step 3 as `QUEUED (offline)` and step 4 as `BLOCKED`.
6. Restores connectivity.
7. Lets the background watcher detect the offline-to-online transition.
8. Automatically calls the existing reconciler.
9. Sends queued work, sets `sent_at`, and re-verifies step 3.
10. Runs step 4 and reaches `COMPLETE`.

No manual `reconcile()` call is required in this demo.

The outbox schema is:

```sql
CREATE TABLE outbox (
  outbox_id TEXT PRIMARY KEY,
  customer_id TEXT NOT NULL,
  refund_id TEXT NOT NULL,
  subject TEXT NOT NULL,
  queued_at TEXT NOT NULL,
  sent_at TEXT
);
```

## Demonstrations

```bash
# Metrics and false-claim comparison
python run_metrics.py

# Data mutation after verification
python demo_stale.py

# Agent attempts to forge evidence
python demo_liar_agent.py

# Offline queue and automatic reconnect recovery
python main.py --offline-demo
```

The default fault modes include:

| Fault mode | Purpose | Expected VERITAS behavior |
|---|---|---|
| `CLEAN` | Normal operation | `COMPLETE` |
| `GHOST_SUCCESS` | Claim success without changing state | Rejects false claim |
| `TIMEOUT_THEN_RECOVER` | First attempt times out | Retry and recover |
| `WRONG_VALUE` | Writes an incorrect value | Detects mismatch |
| `COLLATERAL` | Corrupts an unrelated customer | Detects collateral damage |

## Architecture

```text
PLAN (DAG)
    ↓
PREFLIGHT CHECKER
    ↓
DAG RUNNER
    ↓
EXECUTOR + FAULT INJECTOR
    ↓
AGENT CLAIM
    ↓
INDEPENDENT VERIFIER (read-only DB connection)
    ↓
EVIDENCE LEDGER (hash chain)
    ↓
FAILURE CLASSIFIER
    ↓
RECOVERY ENGINE → RETRY / ESCALATE / STOP
    ↓
COMPLETION GATE
    ↓
TERMINAL OR WEB DASHBOARD
```

The core rule is:

```text
COMPLETE only when every step is independently VERIFIED
```

## Default refund plan

The plan in `agent/plan.py` has four dependent steps:

1. `check_eligibility` — reads the customer eligibility record.
2. `update_refund_db` — creates or updates the processed refund.
3. `send_confirmation_email` — records a sent email, or queues it offline.
4. `log_audit` — records completion after the email is verified.

An agent claim such as “refund completed successfully” is displayed separately
from system truth. The claim is never used as the final proof.

## Offline processing

`harness/network_status.py` performs the connectivity check and exposes
`FORCE_OFFLINE` for demonstrations. When offline,
`agent/tools.py` commits local work and inserts an unsent email into `outbox`.

`recovery/reconciler.py` finds rows where `sent_at IS NULL`, sends them,
updates `sent_at`, and re-runs independent verification for step 3.

`recovery/reconnect_watcher.py` polls connectivity in a background thread and
calls the reconciler when it observes an offline-to-online transition.

The raw internal result for step 3 is currently `FAILED` while the email is
waiting because the verifier correctly refuses to mark an unsent email as
verified. The dashboards recognize the `queued_offline` claim and display the
more meaningful user-facing label `QUEUED (offline)`.

## Evidence, tamper detection, and proof bundles

Every independent verification creates an `Evidence` record containing:

- Step and check identifiers
- Timestamp
- Pass/fail result
- Actual observed details
- Previous and current hashes
- Trust level

`ledger/evidence_ledger.py` links records into a hash chain. A modified record
causes the chain to become unverifiable and the dashboard reports `TAMPERED`.
The ledger summary reports the number of evidence records and its integrity.

Evidence can be exported and checked with `verify_bundle_cli.py`. An untouched
bundle reports `VALID`; changing one byte causes verification to report
`TAMPERED`.

The `Evidence.trust_level` default is `SOFT` so future evidence-producing code
fails closed. The real independent verifier explicitly creates `HARD` evidence.

## Stale data and forged evidence

After a step is verified, another process may change the underlying database.
`DagRunner.mark_stale()` re-checks the state and marks the result `STALE` when
the original evidence no longer describes the current database.

The LiarAgent demonstration shows that forged agent evidence becomes
`UNVERIFIABLE`; the completion gate refuses to report `COMPLETE`.

## Preflight safety checks

`preflight/checker.py` validates the plan using `preflight/rules.yaml` before
`DagRunner.run()` starts. Current rules include:

- A destructive `delete_*` step requires an earlier `backup_*` step.
- A contract must not have an empty `expected` dictionary.

Violations are printed and execution is refused rather than merely warned.

## Database tables

The SQLite schema is in `db/schema.sql`:

| Table | Purpose |
|---|---|
| `customers` | Customer identity and eligibility |
| `refunds` | Refund amount, status, and idempotency key |
| `sent_emails` | Successfully sent confirmations |
| `outbox` | Email work retained during outages |
| `audit_log` | Workflow audit events |
| `users` | Dashboard login identities |
| `otp_challenges` | Hashed OTP challenges and expiry state |

`db/connection.py` provides fresh-world creation and read-write/read-only
connections for the executor and verifier.

## Repository map

```text
agent/       Plan, executor, tools, and LiarAgent
dashboard/   Terminal and web dashboards plus OTP auth
db/          SQLite schema and connection helpers
harness/     Connectivity and fault injection
ledger/      Hash-chained evidence ledger
preflight/   Plan safety rules and checker
recovery/   Recovery decisions, reconciliation, reconnect watcher
runner/      DAG execution, completion gate, and reporting
shared/      Contracts, statuses, evidence, and IDs
verifier/    Independent verification and failure classification
main.py      Main workflow and offline demo entry point
```

## Results

The metrics scenarios demonstrate that naive agent claims can be false while
VERITAS rejects them:

| Fault mode | Naive false claim | VERITAS false claim | VERITAS status |
|---|:---:|:---:|---|
| `CLEAN` | False | False | `COMPLETE` |
| `GHOST_SUCCESS` | True | False | `PARTIAL` |
| `TIMEOUT_THEN_RECOVER` | False | False | `COMPLETE` |
| `WRONG_VALUE` | True | False | `ESCALATED` |
| `COLLATERAL` | False | False | `ESCALATED` |

**Naive false-claim rate: 40% | VERITAS false-claim rate: 0%**

## Current limitations

- The raw internal offline email status is `FAILED`; a future dedicated
  `QUEUED` or `PENDING_RECONCILIATION` enum would be clearer.
- Dashboard sessions are stored in memory and disappear when the server
  restarts.
- The reconnect watcher is a simple polling component suitable for a demo,
  not a production distributed synchronization service.
- SQLite is appropriate for this prototype; a larger deployment may use a
  server database.
- Real SMTP mode requires valid provider credentials and network access.

## Plain-language summary

VERITAS executes refund steps, checks their real database effects independently,
records tamper-evident evidence, detects lies and unexpected changes, preserves
work during outages, automatically reconciles after reconnect, and exposes the
results through an OTP-protected web dashboard.
