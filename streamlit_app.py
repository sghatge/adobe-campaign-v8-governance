import csv
import io
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
    append_history, assess_portfolio, latest_batch,
    load_portfolio, summarize_portfolio,
)
from governance.audit import append_event, read_events, verify_chain
from governance.approval import record_review, read_approvals

st.set_page_config(
    page_title="Governance OS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

POLICY_PATH = ROOT / "config" / "policy.json"
PORTFOLIO_PATH = ROOT / "data" / "synthetic_campaign_portfolio.json"
HISTORY_PATH = ROOT / "data" / "portfolio_assessments.json"
AUDIT_PATH = ROOT / "data" / "audit_ledger.json"
APPROVAL_PATH = ROOT / "data" / "human_approvals.json"

policy = load_json(POLICY_PATH)

st.markdown("""
<style>
.block-container {padding-top: 1.7rem; padding-bottom: 3rem; max-width: 1500px;}
[data-testid="stSidebar"] {background: #101828;}
[data-testid="stSidebar"] * {color: #f8fafc;}
[data-testid="stMetric"] {
  background: #f8fafc; border: 1px solid #e2e8f0;
  padding: 16px; border-radius: 12px;
}
div[data-testid="stMetricValue"] {font-weight: 700;}
div.stButton > button {border-radius: 9px; min-height: 2.6rem; font-weight: 600;}
section[data-testid="stMain"] h1 {letter-spacing: -0.035em;}
.gov-banner {
  padding: 14px 18px; border-radius: 12px;
  background: #eff6ff; color: #1e40af;
  border: 1px solid #bfdbfe; margin-bottom: 18px;
}
.gov-muted {color: #64748b; font-size: .88rem;}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("# 🛡️ GOVERNANCE OS")
    st.caption("ENTERPRISE CAMPAIGN INTELLIGENCE")
    st.divider()
    page = st.radio(
        "WORKSPACE",
        [
            "Executive Overview",
            "Campaign QA",
            "Campaign Portfolio",
            "Risk Intelligence",
            "Approval Centre",
            "Audit Ledger",
            "Policy Registry",
        ],
        label_visibility="visible",
    )
    st.divider()
    st.markdown("**Environment**")
    st.success("Synthetic data only")
    st.caption("V3.1 · Local prototype")
    st.caption(f"Policy {policy['policy_version']}")

st.title(page)
st.markdown(
    '<div class="gov-banner">Independent governance demonstration. '
    'Synthetic data only. No production connection or campaign execution.</div>',
    unsafe_allow_html=True,
)


def get_latest():
    if "v31_results" in st.session_state:
        return st.session_state["v31_results"]
    if HISTORY_PATH.exists():
        return latest_batch(json.loads(HISTORY_PATH.read_text(encoding="utf-8")))
    return []


def run_portfolio():
    campaigns = load_portfolio(PORTFOLIO_PATH)
    results = assess_portfolio(campaigns, policy)
    append_history(HISTORY_PATH, results)
    st.session_state["v31_results"] = results

    for item in results:
        append_event(
            AUDIT_PATH,
            "CAMPAIGN_ASSESSED",
            item["campaign_id"],
            "DETERMINISTIC_QA_ENGINE",
            {
                "decision": item["decision"],
                "risk_level": item["risk_level"],
                "policy_version": item["policy_version"],
                "blocking_count": item["blocking_count"],
            },
        )
    return results


def render_portfolio_table(results):
    rows = [{
        "Campaign": x["campaign_id"],
        "Type": x["campaign_type"],
        "Decision": x["decision"],
        "Risk": x["risk_level"],
        "Blocking checks": x["blocking_count"],
        "Policy": x["policy_version"],
        "Human review": x["investigation_summary"]["human_review"],
    } for x in results]
    st.dataframe(rows, use_container_width=True, hide_index=True)


results = get_latest()

if page == "Executive Overview":
    st.caption("Portfolio health · Governance performance · Operational oversight")
    if not results:
        st.info("No portfolio assessment exists yet. Run your first assessment below.")
    else:
        metrics = summarize_portfolio(results)
        cols = st.columns(4)
        cols[0].metric("Campaigns assessed", metrics["campaign_count"])
        cols[1].metric("APPROVE", metrics["approved"])
        cols[2].metric("BLOCK", metrics["blocked"])
        cols[3].metric("Total findings", metrics["total_findings"])

        cols = st.columns(4)
        cols[0].metric("Critical risk", metrics["critical_campaigns"])
        cols[1].metric("High risk", metrics["high_risk_campaigns"])
        cols[2].metric("Moderate risk", metrics["moderate_risk_campaigns"])
        cols[3].metric("Low risk", metrics["low_risk_campaigns"])

        st.subheader("Portfolio decision distribution")
        st.bar_chart({
            "Campaigns": {
                "APPROVE": metrics["approved"],
                "BLOCK": metrics["blocked"],
            }
        })
        st.subheader("Latest campaign assessments")
        render_portfolio_table(results)

    if st.button("▶ Assess synthetic portfolio", type="primary"):
        try:
            new_results = run_portfolio()
            st.success(f"Assessed {len(new_results)} campaigns.")
            st.rerun()
        except (ValueError, OSError) as exc:
            st.error(str(exc))

elif page == "Campaign QA":
    st.caption("V2 deterministic pre-flight engine and explainable investigation")
    mode = st.radio("Campaign input", ["Bundled example", "Upload JSON"], horizontal=True)
    campaign = None
    if mode == "Bundled example":
        choice = st.selectbox("Synthetic campaign", ["Passing example", "Blocking example"])
        filename = "campaign-pass.json" if choice == "Passing example" else "campaign-fail.json"
        if st.button("Run pre-flight assessment", type="primary"):
            campaign = load_json(ROOT / "samples" / filename)
    else:
        uploaded = st.file_uploader("Upload synthetic campaign JSON", type=["json"])
        if uploaded and st.button("Validate and assess", type="primary"):
            try:
                campaign = parse_campaign_upload(uploaded.getvalue())
            except ValueError as exc:
                st.error(str(exc))

    if campaign is not None:
        qa = evaluate(campaign, policy)
        advisory = investigate(qa)
        if qa["decision"] == "APPROVE":
            st.success("APPROVE — mandatory checks passed.")
        else:
            st.error("BLOCK — mandatory checks failed or remain unknown.")
        cols = st.columns(4)
        for col, label, key in zip(cols, ["PASS", "FAIL", "UNKNOWN", "WARN"],
                                   ["pass", "fail", "unknown", "warn"]):
            col.metric(label, qa["summary"][key])
        st.subheader("Rule-level evidence")
        for check in qa["checks"]:
            with st.expander(f'{check["rule_id"]} · {check["status"]}'):
                st.write(check["message"])
        st.subheader("Explainable investigation")
        st.write("Human review:", advisory["summary"]["human_review"])
        st.write("Decision authority:", advisory["decision_source"])
        for finding in advisory["findings"]:
            with st.expander(f'{finding["risk"]} · {finding["rule_id"]} · {finding["title"]}'):
                st.write(finding["evidence_fact"])
                st.write(finding["explanation"])
                st.write("Evidence to collect:", finding["recommended_evidence"])
        st.download_button(
            "Download combined QA and investigation JSON",
            json.dumps({"qa_report": qa, "investigation_report": advisory}, indent=2),
            file_name="campaign-governance-evidence.json",
            mime="application/json",
        )

elif page == "Campaign Portfolio":
    st.caption("Multi-campaign assessment workspace")
    campaigns = load_portfolio(PORTFOLIO_PATH)
    st.metric("Synthetic campaigns available", len(campaigns))
    if st.button("▶ Assess entire portfolio", type="primary"):
        try:
            new_results = run_portfolio()
            st.success(f"Assessment completed for {len(new_results)} campaigns.")
            st.rerun()
        except (ValueError, OSError) as exc:
            st.error(str(exc))
    results = get_latest()
    if results:
        render_portfolio_table(results)
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=list({
            "Campaign": "", "Type": "", "Decision": "", "Risk": "",
            "Blocking checks": "", "Policy": "", "Human review": "",
        }.keys()))
        writer.writeheader()
        for item in results:
            writer.writerow({
                "Campaign": item["campaign_id"],
                "Type": item["campaign_type"],
                "Decision": item["decision"],
                "Risk": item["risk_level"],
                "Blocking checks": item["blocking_count"],
                "Policy": item["policy_version"],
                "Human review": item["investigation_summary"]["human_review"],
            })
        st.download_button(
            "⬇ Download portfolio CSV", buffer.getvalue(),
            "governance-portfolio.csv", "text/csv",
        )

elif page == "Risk Intelligence":
    st.caption("Cross-campaign control failure patterns and risk concentration")
    if not results:
        st.info("Run a portfolio assessment to populate risk intelligence.")
    else:
        metrics = summarize_portfolio(results)
        cols = st.columns(3)
        cols[0].metric("Critical campaigns", metrics["critical_campaigns"])
        cols[1].metric("High-risk campaigns", metrics["high_risk_campaigns"])
        cols[2].metric("Control failure types", len(metrics["control_failures"]))
        failures = metrics["control_failures"]
        if failures:
            st.subheader("Control failure frequency")
            st.bar_chart(failures)
            st.dataframe(
                [{"Control": k, "Occurrences": v} for k, v in failures.items()],
                use_container_width=True, hide_index=True,
            )
        st.subheader("Risk by campaign")
        st.dataframe(
            [{"Campaign": x["campaign_id"], "Decision": x["decision"],
              "Risk": x["risk_level"], "Findings": x["investigation_summary"]["finding_count"]}
             for x in results],
            use_container_width=True, hide_index=True,
        )

elif page == "Approval Centre":
    st.caption("Human accountability workspace. No campaign execution or release.")
    if not results:
        st.info("Run a portfolio assessment before opening review cases.")
    else:
        approvals = read_approvals(APPROVAL_PATH)
        reviewed = {x["campaign_id"] for x in approvals}
        pending = [x for x in results if
                   x["investigation_summary"]["human_review"] == "PENDING"
                   and x["campaign_id"] not in reviewed]
        blocked = [x for x in results if x["decision"] == "BLOCK"]

        cols = st.columns(3)
        cols[0].metric("Pending review cases", len(pending))
        cols[1].metric("Blocked campaigns", len(blocked))
        cols[2].metric("Review records", len(approvals))

        if blocked:
            st.error("BLOCKED campaigns are not eligible for approval or release.")
            st.dataframe(
                [{"Campaign": x["campaign_id"], "Decision": "BLOCK",
                  "Action": "Resolve control failures and reassess"}
                 for x in blocked],
                use_container_width=True, hide_index=True,
            )

        if pending:
            options = {f'{x["campaign_id"]} · {x["decision"]} · {x["risk_level"]}': x
                       for x in pending}
            selected_label = st.selectbox("Select review case", list(options))
            selected = options[selected_label]
            st.write("Deterministic decision:", selected["decision"])
            st.write("Risk:", selected["risk_level"])
            reviewer = st.text_input("Reviewer identity")
            action_options = (
                ["REJECT", "REQUEST_CHANGES"] if selected["decision"] == "BLOCK"
                else ["APPROVE", "REJECT", "REQUEST_CHANGES"]
            )
            action = st.selectbox("Review action", action_options)
            comment = st.text_area("Review rationale (required)")
            if st.button("Record human review", type="primary"):
                try:
                    record = record_review(
                        APPROVAL_PATH, AUDIT_PATH, selected["campaign_id"],
                        selected["decision"], reviewer, action, comment,
                    )
                    st.success(f'Review recorded: {record["review_id"]}')
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
        else:
            st.info("No unreviewed human-review cases in the latest batch.")

        if approvals:
            st.subheader("Review history")
            st.dataframe(approvals, use_container_width=True, hide_index=True)

elif page == "Audit Ledger":
    st.caption("Assessment and human-review event history")
    events = read_events(AUDIT_PATH)
    intact = verify_chain(events)
    cols = st.columns(3)
    cols[0].metric("Audit events", len(events))
    cols[1].metric("Chain integrity", "VALID" if intact else "INVALID")
    cols[2].metric("Latest sequence", events[-1]["sequence"] if events else 0)
    if intact:
        st.success("Hash-chain verification passed.")
    else:
        st.error("Audit integrity failure. New events are refused.")
    if events:
        st.dataframe(
            [{"Sequence": e["sequence"], "Timestamp": e["timestamp"],
              "Event": e["event_type"], "Campaign": e["campaign_id"],
              "Actor": e["actor"], "Hash": e["event_hash"][:16] + "..."}
             for e in reversed(events)],
            use_container_width=True, hide_index=True,
        )
        st.download_button(
            "⬇ Download audit ledger JSON",
            json.dumps(events, indent=2),
            "governance-audit-ledger.json",
            "application/json",
        )
    else:
        st.info("No audit events recorded yet.")

elif page == "Policy Registry":
    st.caption("Current deterministic policy configuration")
    st.json(policy)
    st.warning(
        "Policy editing and version migration are not enabled in this release. "
        "The active policy remains the authority for deterministic assessment."
    )

st.divider()
st.caption(
    "Governance boundary: deterministic QA owns APPROVE/BLOCK. "
    "Human review records accountability but cannot release a BLOCK campaign. "
    "Local hash chaining is tamper-evident, not a production immutable ledger."
)
