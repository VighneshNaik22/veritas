# VERITAS — Evidence-Gated Self-Healing Agent Workflow

Zero-trust AI agent: every action is independently verified against real
database state before being trusted. The agent never grades its own homework.

## Setup

```bash
pip install -r requirements.txt
python main.py
```

Web dashboard:

```bash
python run_dashboard.py
# open the forwarded port 8000 URL
```

The dashboard runs the real workflow against SQLite and shows independent
verification results, evidence-chain integrity, preflight state, and the
persisted refund/email/outbox records. Use the scenario selector to inspect
clean and injected-fault runs.

Dashboard login:

- The seeded demo account is `demo@example.com`.
- Request a login code from the dashboard login page.
- Local development uses `VERITAS_AUTH_DEV_MODE=1` by default and prints the
  one-time code with a `DEV ONLY` marker for demonstration only.
- For real delivery, set `VERITAS_SMTP_USER`, `VERITAS_SMTP_PASSWORD`,
  and optionally `VERITAS_SMTP_HOST`, `VERITAS_SMTP_PORT`, and
  `VERITAS_SMTP_FROM`, then set `VERITAS_AUTH_DEV_MODE=0`. The defaults
  are Gmail's `smtp.gmail.com:587`; `VERITAS_SMTP_FROM` defaults to the
  SMTP user.
- Set `VERITAS_OTP_PEPPER` to a long random secret in non-demo
  environments.
- OTPs are stored only as HMAC-SHA256 hashes, expire after five minutes, are
  single-use, and allow at most three requests per IP per fifteen minutes
  plus five verification attempts per challenge.

Additional demonstrations:

```bash
python run_metrics.py
python demo_stale.py
python demo_liar_agent.py
python main.py --offline-demo
```

`verify_bundle_cli.py` independently validates exported evidence bundles.

## Architecture

```
PLAN (hard-coded DAG) → DAG RUNNER → EXECUTOR (+FAULT INJECTOR) → CLAIM
                                                                      │
                                                                      ▼
                                              INDEPENDENT VERIFIER (read-only DB conn)
                                              │ re-checks real state, never trusts the claim
                                                                      ▼
                                                            EVIDENCE LEDGER (hash-chained)
                                                                      │
                                                                      ▼
                                                              FAILURE CLASSIFIER
                                        NONE / NO_EFFECT / WRONG_VALUE / DUPLICATE / COLLATERAL / TIMEOUT
                                                                      │
                                                                      ▼
                                                       RECOVERY ENGINE → RETRY / ESCALATE / STOP
                                                                      │
                                                                      ▼
                                              COMPLETION GATE: COMPLETE only if every
                                          step is VERIFIED — otherwise PARTIAL / FAILED / ESCALATED
                                                                      │
                                                                      ▼
                                          PROOF-CARRYING REPORT + CLAIM-VS-TRUTH DASHBOARD
```

## Results — false-claim rate (naive vs VERITAS)

| Fault Mode            | Naive False Claim | VERITAS False Claim | VERITAS Status |
|------------------------|:------------------:|:---------------------:|-----------------|
| CLEAN                  | False              | False                 | COMPLETE        |
| GHOST_SUCCESS          | True               | False                  | PARTIAL         |
| TIMEOUT_THEN_RECOVER   | False              | False                  | COMPLETE        |
| WRONG_VALUE            | True               | False                  | ESCALATED       |
| COLLATERAL             | False              | False                  | ESCALATED       |

**Naive: 40% false claims | VERITAS: 0% false claims**