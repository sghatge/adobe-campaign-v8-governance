import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from acc_v8_qa.engine import evaluate, load_json
from acc_v8_qa.dashboard import parse_campaign_upload
from acc_v8_qa.investigation import investigate

st.set_page_config(
    page_title="Campaign Governance Console",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ Campaign Governance Console")
st.caption("Deterministic pre-flight QA | Explainable investigation | Synthetic data")

st.info(
    "Independent demonstration. No production connection or campaign execution. "
    "Use synthetic data only."
)

policy = load_json(ROOT / "config" / "policy.json")

st.sidebar.header("Assessment settings")
st.sidebar.write("Policy version:", policy["policy_version"])
st.sidebar.write(
    "Audience variance limit:",
    f'{policy["audience_drift_limit"]:.0%}',
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
        help="Maximum 256 KB. Synthetic data only.",
    )
    if uploaded is not None and st.button(
        "Validate and assess", type="primary"
    ):
        try:
            campaign = parse_campaign_upload(uploaded.getvalue())
        except ValueError as exc:
            input_error = str(exc)

if input_error:
    st.error(input_error)

if campaign is not None:
    qa_report = evaluate(campaign, policy)
    advisory = investigate(qa_report)

    st.divider()
    st.subheader("1. Deterministic QA decision")

    if qa_report["decision"] == "APPROVE":
        st.success("APPROVE — all mandatory checks passed.")
    else:
        st.error("BLOCK — mandatory checks failed or remain unknown.")

    summary = qa_report["summary"]
    cols = st.columns(4)
    for col, (label, value) in zip(cols, [
        ("PASS", summary["pass"]),
        ("FAIL", summary["fail"]),
        ("UNKNOWN", summary["unknown"]),
        ("WARN", summary["warn"]),
    ]):
        col.metric(label, value)

    st.write("**Campaign reference:**", qa_report["campaign_id"])
    st.write("**Policy version:**", qa_report["policy_version"])
    st.write("**Blocking checks:**", qa_report["blocking_count"])

    st.subheader("Rule-level evidence")
    for item in qa_report["checks"]:
        status = item["status"]
        with st.expander(
            f'{item["rule_id"]} — {status}',
            expanded=status in ("FAIL", "UNKNOWN"),
        ):
            st.write(item["message"])

    st.divider()
    st.subheader("2. Explainable investigation")
    st.caption(
        "Offline advisory mode. No LLM or external service is called. "
        "The investigation layer cannot override the deterministic decision."
    )

    overview = advisory["summary"]
    cols = st.columns(4)
    cols[0].metric("Findings", overview["finding_count"])
    cols[1].metric("Critical", overview["critical"])
    cols[2].metric("High", overview["high"])
    cols[3].metric("Low", overview["low"])

    st.write("**Human review:**", overview["human_review"])
    st.write(
        "**Decision authority:**",
        advisory["decision_source"],
    )

    if not advisory["findings"]:
        st.success("No advisory findings were generated.")
    else:
        for finding in advisory["findings"]:
            with st.expander(
                f'{finding["risk"]} | {finding["rule_id"]} — {finding["title"]}',
                expanded=finding["risk"] == "CRITICAL",
            ):
                st.write("**Observed evidence:**", finding["evidence_fact"])
                st.write("**Explanation:**", finding["explanation"])
                st.write("**Confidence:**", finding["confidence"])
                st.write("**Evidence to collect:**")
                for evidence in finding["recommended_evidence"]:
                    st.write(f"- {evidence}")

    st.divider()
    st.subheader("3. Combined audit evidence")

    combined_report = {
        "qa_report": qa_report,
        "investigation_report": advisory,
    }
    report_json = json.dumps(combined_report, indent=2)

    st.download_button(
        "⬇️ Download combined QA and investigation report",
        data=report_json,
        file_name="campaign-governance-evidence.json",
        mime="application/json",
    )

    with st.expander("View complete combined JSON"):
        st.json(combined_report)

st.divider()
st.caption(
    "Governance boundary: deterministic controls own APPROVE/BLOCK. "
    "Investigation is read-only advisory guidance. No execution or automatic override."
)
