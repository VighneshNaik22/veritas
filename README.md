# VERITAS — Evidence-Gated Self-Healing Agent Workflow

Zero-trust AI agent: every action is independently verified against real
database state before being trusted. The agent never grades its own homework.

## Setup

```bash
pip install rich
python main.py
```

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