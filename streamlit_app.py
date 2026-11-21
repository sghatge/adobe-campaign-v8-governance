import json
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from acc_v8_qa.engine import evaluate, load_json
from acc_v8_qa.dashboard import parse_campaign_upload
from acc_v8_qa.investigation import investigate
from governance.portfolio import (
    append_history,
    assess_portfolio,
    latest_batch,
    load_portfolio,
    summarize_portfolio,
)


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


# ============================================================
# V3: Enterprise Governance Portfolio Control Tower
# ============================================================

st.divider()
st.title("🏢 V3 — Enterprise Governance Control Tower")
st.caption(
    "Multi-campaign portfolio intelligence | Local JSON storage | Synthetic data only"
)

PORTFOLIO_PATH = ROOT / "data" / "synthetic_campaign_portfolio.json"
HISTORY_PATH = ROOT / "data" / "portfolio_assessments.json"

try:
    portfolio_campaigns = load_portfolio(PORTFOLIO_PATH)
    st.info(
        f"Synthetic portfolio loaded: {len(portfolio_campaigns)} campaigns. "
        "Assessments use the existing V2 deterministic engine and investigation layer."
    )

    left, right = st.columns([1, 3])
    with left:
        run_portfolio = st.button(
            "▶ Assess entire portfolio",
            type="primary",
            key="v3_assess_portfolio",
        )
    with right:
        st.caption("Assessment history is stored locally in data/portfolio_assessments.json.")

    if run_portfolio:
        results = assess_portfolio(portfolio_campaigns, policy)
        append_history(HISTORY_PATH, results)
        st.session_state["v3_latest_results"] = results
        st.success(f"Assessment completed for {len(results)} campaigns.")

    if "v3_latest_results" in st.session_state:
        portfolio_results = st.session_state["v3_latest_results"]
    else:
        if HISTORY_PATH.exists():
            import json as _json
            stored_history = _json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
            portfolio_results = latest_batch(stored_history)
        else:
            portfolio_results = []

    if portfolio_results:
        metrics = summarize_portfolio(portfolio_results)

        st.subheader("Portfolio executive scorecard")
        metric_cols = st.columns(4)
        metric_cols[0].metric("Campaigns assessed", metrics["campaign_count"])
        metric_cols[1].metric("APPROVE", metrics["approved"])
        metric_cols[2].metric("BLOCK", metrics["blocked"])
        metric_cols[3].metric("Total findings", metrics["total_findings"])

        risk_cols = st.columns(4)
        risk_cols[0].metric("Critical risk", metrics["critical_campaigns"])
        risk_cols[1].metric("High risk", metrics["high_risk_campaigns"])
        risk_cols[2].metric("Moderate risk", metrics["moderate_risk_campaigns"])
        risk_cols[3].metric("Low risk", metrics["low_risk_campaigns"])

        st.subheader("Campaign portfolio")
        table_rows = []
        for item in portfolio_results:
            table_rows.append({
                "Campaign": item["campaign_id"],
                "Type": item["campaign_type"],
                "Segment": item["segment"],
                "Decision": item["decision"],
                "Risk": item["risk_level"],
                "Blocking checks": item["blocking_count"],
                "Policy": item["policy_version"],
                "Human review": item["investigation_summary"]["human_review"],
            })

        st.dataframe(table_rows, use_container_width=True, hide_index=True)

        st.subheader("Governance control failure frequency")
        failures = metrics["control_failures"]
        if failures:
            failure_rows = [
                {"Control": key, "FAIL / UNKNOWN occurrences": value}
                for key, value in failures.items()
            ]
            st.bar_chart(
                {row["Control"]: row["FAIL / UNKNOWN occurrences"]
                 for row in failure_rows}
            )
            st.dataframe(failure_rows, use_container_width=True, hide_index=True)
        else:
            st.success("No failing or unknown controls in this assessment batch.")

        st.subheader("Campaign investigation details")
        for item in portfolio_results:
            with st.expander(
                f'{item["campaign_id"]} | {item["decision"]} | {item["risk_level"]}'
            ):
                st.write("**Campaign type:**", item["campaign_type"])
                st.write("**Policy version:**", item["policy_version"])
                st.write("**Human review:**", item["investigation_summary"]["human_review"])
                for finding in item["investigation_findings"]:
                    st.write(
                        f'- **{finding["risk"]} — {finding["rule_id"]}:** '
                        f'{finding["evidence_fact"]}'
                    )

        import csv as _csv
        import io as _io

        csv_buffer = _io.StringIO()
        writer = _csv.DictWriter(
            csv_buffer,
            fieldnames=list(table_rows[0].keys()),
        )
        writer.writeheader()
        writer.writerows(table_rows)

        st.download_button(
            "⬇️ Download portfolio assessment CSV",
            data=csv_buffer.getvalue(),
            file_name="synthetic-governance-portfolio.csv",
            mime="text/csv",
            key="v3_portfolio_csv",
        )

        st.caption(
            "Portfolio metrics are descriptive summaries. "
            "They do not replace campaign-level deterministic decisions or approvals."
        )
    else:
        st.warning(
            "No portfolio assessment history yet. Select 'Assess entire portfolio' "
            "to run the first synthetic batch."
        )

except (ValueError, OSError) as exc:
    st.error(f"Portfolio could not be loaded: {exc}")


