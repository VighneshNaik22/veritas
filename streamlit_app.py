import streamlit as st

from db.connection import build_fresh_world
from main import run_veritas
from shared.contracts import StepStatus


st.set_page_config(
    page_title="VERITAS Trust Console",
    page_icon="🛡️",
    layout="wide",
)

st.title("VERITAS Trust Console")
st.caption(
    "Zero-trust workflow observability: agent claims versus independently "
    "verified database truth."
)

fault_mode = st.selectbox(
    "Scenario",
    [
        "CLEAN",
        "GHOST_SUCCESS",
        "TIMEOUT_THEN_RECOVER",
        "WRONG_VALUE",
        "COLLATERAL",
    ],
)

if st.button("Run workflow", type="primary"):
    fault_map = (
        {}
        if fault_mode == "CLEAN"
        else {"step_2": fault_mode}
    )

    build_fresh_world()
    status, results = run_veritas(fault_map)
    ledger = run_veritas.last_ledger

    st.session_state["status"] = status.value
    st.session_state["results"] = results
    st.session_state["ledger"] = ledger

if "status" not in st.session_state:
    st.info("Choose a scenario and click Run workflow.")
    st.stop()

status = st.session_state["status"]
results = st.session_state["results"]
ledger = st.session_state["ledger"]

status_colors = {
    "COMPLETE": "normal",
    "PARTIAL": "off",
    "FAILED": "inverse",
    "ESCALATED": "inverse",
}

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Run status", status)

with col2:
    evidence_count = ledger.conn.execute(
        "SELECT COUNT(*) FROM evidence"
    ).fetchone()[0]
    st.metric("Evidence records", evidence_count)

with col3:
    chain_valid = ledger.verify_chain_bool()
    st.metric("Ledger integrity", "VERIFIED" if chain_valid else "TAMPERED")

st.divider()
st.subheader("Workflow truth table")

rows = []

for step_id, result in results.items():
    evidence = result.evidence

    if "queued_offline" in (result.claim or "").lower():
        display_status = "QUEUED (offline)"
    else:
        display_status = result.status.value

    rows.append(
        {
            "Step": step_id,
            "Agent claim": result.claim or "—",
            "Verified truth": (
                "Matches observed state"
                if evidence and evidence.passed
                else "Does not match observed state"
                if evidence
                else "No verification record"
            ),
            "Status": display_status,
            "Failure class": result.failure_class.value,
            "Attempts": result.attempts,
        }
    )

st.dataframe(rows, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Evidence chain")

chain_rows = [
    {
        "Evidence ID": evidence_id,
        "Integrity": chain_status,
    }
    for evidence_id, chain_status in ledger.verify_chain()
]

st.dataframe(chain_rows, use_container_width=True, hide_index=True)

st.divider()
st.subheader("Verified evidence details")

for step_id, result in results.items():
    with st.expander(step_id):
        st.write(
            {
                "status": result.status.value,
                "claim": result.claim,
                "failure_class": result.failure_class.value,
                "attempts": result.attempts,
                "escalated": result.escalated,
                "evidence": (
                    {
                        "passed": result.evidence.passed,
                        "details": result.evidence.details,
                        "trust_level": result.evidence.trust_level,
                        "evidence_id": result.evidence.evidence_id,
                    }
                    if result.evidence
                    else None
                ),
            }
        )