# VERITAS — Master Build Plan (3 people, 5–6 hours)

This is the plan that ties together the three individual agent files
(`member1_trust_layer_AGENT.md`, `member2_control_layer_AGENT.md`,
`member3_agent_demo_layer_AGENT.md`). Read this one first as a team, together,
before anyone opens an editor.

---

## 0. Reality check — why this plan looks nothing like your source docs

Your `AGENT.md` and the "VERITAS" doc from your friend's AI chat describe a
**20–22 hour build for a 4–5 person team** (the second doc even adds ZK
proofs, TEEs, Z3 formal verification, and a "multi-agent swarm governance"
layer). You have **3 people and 5–6 hours** — roughly 15–18 person-hours
total. That is about **12–15% of the time** those docs assume.

Trying to build the full thing will leave you with nothing working. This
plan builds a **smaller, fully-working core** that hits every judging
criterion the problem statement actually asks for:

- zero-trust (agent's claims are never believed)
- evidence-gated (a step is only "done" when code — not an LLM — checks it)
- self-healing (classifies failures, recovers, or safely stops)
- no false completion (a hard completion gate)
- a working demo with injected failures and a headline metric

**Explicitly OUT OF SCOPE for the 5–6 hour build** (name-drop these in your
pitch as "what we'd add with more time" — that shows judges you understood
the full design space without you having to build it):

| Cut | Replaced with |
|---|---|
| Ed25519 signing + Merkle trees | Plain SHA-256 hash-chained ledger (still tamper-evident, ~40 lines) |
| Streamlit web dashboard | Rich terminal dashboard only |
| Docker / Docker Compose | Just run `python main.py` |
| OAuth 2.1 / SPIFFE zero-trust auth | A real read-only SQLite connection (`mode=ro`) is your zero-trust story |
| OpenTelemetry | Plain print/Rich logging |
| LLM-based planner | A hard-coded plan (`agent/plan.py`) — still a real DAG with contracts |
| Mutation-tested contract strength, liar agent, STALE detection, signed proof bundle CLI, YAML pre-flight checker | Listed as future work only |
| Z3 formal verification, ZK-policy proofs, TEEs, multi-agent swarm, "emotional bank" | Not real hackathon scope for any team size in 6 hours — skip entirely, don't mention as "future work" either, they'll invite questions you can't answer |

---

## 1. The demo scenario (fixed — do not change mid-build)

**Task:** "Process refund for customer C123: verify eligibility, update the
refund DB, send confirmation email, log audit trail."

**4-step plan (a linear chain — depends_on makes it a DAG, but for the demo
it's step1 → step2 → step3 → step4):**

1. `check_eligibility` (C123) — read-only check
2. `update_refund_db` (R123, $50.00) — **this is the only step fault modes
   target**
3. `send_confirmation_email` (irreversible — never auto-retried)
4. `log_audit`

**Why all faults hit step 2 only:** if step 2 never verifies, step 3 and 4
are **BLOCKED** — which means the irreversible email is never sent on a bad
run. That's your single best demo line: *"the email that can't be unsent
never left the building."*

**Fault modes (build in this order):**

| Order | Mode | What it proves |
|---|---|---|
| 1 | `GHOST_SUCCESS` | tool says "success", DB never changes → zero-trust catches it |
| 2 | `TIMEOUT_THEN_RECOVER` | fails once, verifier says "not done yet", retries, succeeds → self-healing works |
| 3 | `WRONG_VALUE` | tool writes $5 instead of $50, claims success → evidence-gating catches wrong data, not just missing data |
| 4 (only if time remains) | `COLLATERAL` | fixes the right row but silently corrupts another customer's row → hardest to build, cut first if short on time |

Full technical spec (schema, contracts, code) is identical across all three
member files — see any of them for the exact `shared/contracts.py` and
`db/schema.sql`.

---

## 2. Team split and why it merges cleanly

```
Member 1 — TRUST LAYER        Member 2 — CONTROL LAYER      Member 3 — AGENT/DEMO LAYER
(standalone, no dependency    (depends on Member 1's        (depends on Member 1's DB
 on teammates' code)           interfaces + a stub           schema + Member 2's
                                executor to start)            DagRunner interface;
                                                               owns main.py)
─────────────────────         ─────────────────────         ─────────────────────
db/schema.sql                 runner/dag_runner.py           agent/plan.py
db/connection.py               runner/completion_gate.py     agent/tools.py
ledger/evidence_ledger.py     runner/report_generator.py    agent/executor.py
verifier/checker.py           recovery/recovery_engine.py   harness/fault_injection.py
verifier/independent_verifier.py                             harness/baseline_agents.py
verifier/failure_classifier.py                                harness/metrics.py
                                                               dashboard/terminal_view.py
                                                               main.py
```

The dependency arrow only ever points one way: **1 → 2 → 3**. That means:

- Member 1 can build and test their whole piece against nothing but the SQLite
  file — no waiting on anyone.
- Member 2 needs Member 1's `verify()`/`classify()` shape, which is fixed by
  `shared/contracts.py` from minute 20 — they build against a **fake
  executor stub** (given in their file) until Member 3's real one is ready.
- Member 3 needs the DB schema (fixed at minute 20) and Member 2's
  `DagRunner` interface — they build against a **fake DAG runner stub**
  (given in their file) until Member 2's real one is ready.

Nobody is blocked past the first 20 minutes.

`shared/contracts.py` is the one file all three must agree on **before**
splitting up — it's pasted identically into all three member files. **Do
not change field names in it after minute 20** without telling both other
people; every module imports from it.

---

## 3. Hour-by-hour schedule (6 hours = 360 min)

| Time | Block | Who | What |
|---|---|---|---|
| 0:00–0:20 | Kickoff | All 3 | Agree on the demo scenario (above, don't change it), create the repo, all three paste `shared/contracts.py` and `db/schema.sql` in place (from any member's file — they're identical). `pip install rich`. |
| 0:20–2:30 | Deep build, part 1 | Each on own track | Build against `contracts.py` + the stub code given in your own file for the piece you don't own yet. Don't wait on teammates. |
| 2:30–2:45 | Sync | All 3 | 5 min each: "what's done, what's blocked, what's risky." If someone's stuck, paste the error into this chat now — don't sit on it. |
| 2:45–4:00 | Deep build, part 2 | Each on own track | Finish your module. By the end of this block your module should pass its own local test (each file lists one). |
| 4:00–4:45 | **Integration** | All 3, together, one screen | Member 3 wires `main.py`: real `DagRunner` (Member 2) + real `IndependentVerifier`/`classify` (Member 1) + real `Executor`/`FaultInjector` (Member 3). Run the CLEAN plan first (no faults) — it must end **COMPLETE**. Then run `GHOST_SUCCESS` on step 2 — it must end **PARTIAL**, with step 3/4 **BLOCKED**. |
| 4:45–5:15 | Fault sweep | All 3 | Run all built fault modes + the naive-agent comparison (`harness/metrics.py`). Fix whatever breaks. If `COLLATERAL` isn't working, cut it — 3 solid fault modes beat 4 broken ones. |
| 5:15–5:40 | Polish | All 3 | README (setup steps + the real numbers your metrics run produced), demo script filled in with your actual headline number (see §5), threat-model bullet list. |
| 5:40–6:00 | Rehearse | All 3 | Full dry run of the live demo, or record a 90-second backup video in case live demo breaks. |

**If you only have 5 hours:** cut the 2:30 sync to 5 min inline (don't
stop building), and cut rehearsal to 10 min. Do **not** cut the 4:00–4:45
integration block — that's the one that actually produces a working demo.

---

## 4. Definition of done (Tier 1 — this is your whole demo)

- [ ] `python main.py` with no fault injected ends **COMPLETE**, all 4 steps
      show `VERIFIED` in the terminal dashboard.
- [ ] `GHOST_SUCCESS` on step 2 ends **PARTIAL** (or `FAILED`), step 2 shows a
      claim of "success" next to a truth column that disagrees, in red; step
      3 and 4 show **BLOCKED**.
- [ ] `TIMEOUT_THEN_RECOVER` on step 2 retries once and ends **COMPLETE** —
      this is your "self-healing" moment.
- [ ] `WRONG_VALUE` on step 2 ends **ESCALATED**, and the final report
      explicitly says it needs human approval rather than claiming success.
- [ ] `harness/metrics.py` prints a table comparing the naive agent
      (trusts the tool blindly) against VERITAS across all fault modes,
      with a real false-claim-rate number for each — not the 76%/0.8%
      numbers from the docs, **your actual numbers** from your actual run.
- [ ] `ledger.verify_chain()` returns `True` on a normal run, and `False`
      if you manually edit one byte in the ledger's SQLite file — this is
      your "tamper-evident" proof point, worth 15 seconds in the demo.
- [ ] `COLLATERAL` fault mode — **stretch**, cut first if short on time.

If everything above is checked, you have a complete, honest, working demo.
Anything past this (signed receipts, web dashboard, STALE detection) is
pure upside — do not start it until this list is fully green.

---

## 5. Demo script (fill in the blanks with your real numbers)

**Opening (20s):** "Agents lie about success constantly — one 2026 study
found false-completion claims make up 44–76% of agent failures. We built
VERITAS: an agent that never gets to grade its own homework."

**Demo (100s):**
1. Run the clean task — VERITAS says COMPLETE, all 4 steps verified.
2. Run with `GHOST_SUCCESS` on the refund-DB step — tool says success,
   dashboard flashes red, DB is untouched. Point at the BLOCKED steps:
   "the confirmation email that can't be unsent never went out."
3. Run with `TIMEOUT_THEN_RECOVER` — show it retry and self-heal to COMPLETE.
4. Run with `WRONG_VALUE` — show it refuse to say COMPLETE and escalate
   instead of quietly reporting the wrong number.
5. Show the metrics table: naive agent's false-claim rate vs. VERITAS's
   (your real numbers).
6. (If time) tamper one byte in the ledger file, run `verify_chain()` live,
   show it fail.

**Closing (20s):** state your real false-claim-rate numbers, then: "COMPLETE
is unreachable in our system without independently verified evidence for
every single step."

---

## 6. If you hit a wall mid-build

Come back to this chat and tell me:
1. Which of the three members you are.
2. The exact file you're editing.
3. The full error / traceback, or the exact wrong behavior you're seeing.
4. The current content of that file (paste it).

I'll hand back corrected, drop-in code. Don't spend more than ~10 minutes
stuck on any single error before doing this — you don't have spare hours.
