import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from acc_v8_qa.engine import evaluate, load_json
from acc_v8_qa.dashboard import parse_campaign_upload

st.set_page_config(
    page_title="Campaign Governance Console",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ Campaign Governance Console")
st.caption(
    "Deterministic pre-flight validation | "
    "Synthetic reference implementation"
)

st.info(
    "Independent demonstration only. This application does not connect "
    "to Adobe Campaign or execute campaigns. Use synthetic data only."
)

policy_path = ROOT / "config" / "policy.json"
policy = load_json(policy_path)

st.sidebar.header("Assessment settings")
st.sidebar.write("Policy version:", policy["policy_version"])
st.sidebar.write(
    "Audience variance limit:",
    f'{policy["audience_drift_limit"]:.0%}'
)
st.sidebar.write("Maximum JSON size: 256 KB")

mode = st.radio(
    "Choose campaign input",
    ["Bundled example", "Upload JSON"],
    horizontal=True,
)

campaign = None
input_error = None

if mode == "Bundled example":
    example = st.selectbox(
        "Select synthetic campaign",
        ["Passing example", "Blocking example"],
    )

    filename = (
        "campaign-pass.json"
        if example == "Passing example"
        else "campaign-fail.json"
    )

    if st.button("Run pre-flight assessment", type="primary"):
        campaign = load_json(ROOT / "samples" / filename)

else:
    uploaded = st.file_uploader(
        "Upload campaign JSON",
        type=["json"],
        help="Maximum size 256 KB. Synthetic data only.",
    )

    if uploaded is not None:
        raw = uploaded.getvalue()

        if st.button("Validate and assess", type="primary"):
            try:
                campaign = parse_campaign_upload(raw)
            except ValueError as exc:
                input_error = str(exc)

if input_error:
    st.error(input_error)

if campaign is not None:
    report = evaluate(campaign, policy)

    st.divider()
    st.subheader("Assessment result")

    decision = report["decision"]

    if decision == "APPROVE":
        st.success("APPROVE — all mandatory checks passed.")
    else:
        st.error("BLOCK — mandatory checks failed or remain unknown.")

    summary = report["summary"]

    cols = st.columns(4)
    metrics = [
        ("PASS", summary["pass"]),
        ("FAIL", summary["fail"]),
        ("UNKNOWN", summary["unknown"]),
        ("WARN", summary["warn"]),
    ]

    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)

    st.write("**Campaign reference:**", report["campaign_id"])
    st.write("**Policy version:**", report["policy_version"])
    st.write("**Blocking checks:**", report["blocking_count"])

    st.divider()
    st.subheader("Rule-level evidence")

    for item in report["checks"]:
        status = item["status"]
        title = f'{item["rule_id"]} — {status}'

        with st.expander(title, expanded=status in ("FAIL", "UNKNOWN")):
            st.write(item["message"])

    st.divider()
    st.subheader("Evidence report")

    report_json = json.dumps(report, indent=2)

    st.download_button(
        "⬇️ Download JSON evidence report",
        data=report_json,
        file_name="campaign-qa-evidence.json",
        mime="application/json",
    )

    with st.expander("View complete JSON report"):
        st.json(report)

st.divider()
st.caption(
    "Governance boundary: AI assistance is not part of this release. "
    "Only the deterministic engine decides APPROVE or BLOCK. "
    "No campaign execution or automatic override is available."
)
