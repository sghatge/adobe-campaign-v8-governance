import csv
import importlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))
importlib.invalidate_caches()

# Streamlit may rerun this script in a process that still has local modules
# cached from the prior deployed revision. Refresh these two updated modules so
# the Phase 2 exports are available after a repository update.
for _module_name in ("governance.audit", "governance.campaign_guardian"):
    _cached_module = sys.modules.get(_module_name)
    if _cached_module is not None:
        importlib.reload(_cached_module)

import streamlit as st

from acc_v8_qa.engine import evaluate, load_json
from acc_v8_qa.dashboard import parse_campaign_upload
from acc_v8_qa.investigation import investigate
from governance.portfolio import (
    append_history, assess_portfolio, latest_batch,
    load_portfolio, summarize_portfolio,
)
from governance.audit import (
    append_event, export_ledger, read_events, verify_chain, verify_chain_report,
)
from governance.approval import record_review, read_approvals
from governance.campaign_guardian import (
    MAX_ITERATIONS, create_candidate_playbook, read_playbooks,
    reviewer_evidence_improver, playbook_diff, review_candidate_playbook,
    run_bounded_improvement_loop,
)

st.set_page_config(
    page_title="Governance OS",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# GOVERNANCE_OS_V32_THEME
st.markdown("""
<style>
:root {
  --gov-navy: #101a2b;
  --gov-blue: #2864dc;
  --gov-cyan: #22a6a1;
  --gov-ink: #172338;
  --gov-muted: #718096;
  --gov-border: #e4eaf2;
  --gov-surface: #ffffff;
  --gov-soft: #f4f7fb;
}
.stApp {
  background: #f5f7fb;
  color: var(--gov-ink);
}
[data-testid="stHeader"] {
  background: rgba(245,247,251,0.92);
}
[data-testid="stMainBlockContainer"] {
  max-width: 1500px;
  padding-top: 2rem;
  padding-bottom: 3rem;
}
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #101a2b 0%, #17263c 100%);
  border-right: 1px solid #26364d;
}
[data-testid="stSidebar"] * {
  color: #edf3fc;
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
  color: #b8c6d9;
}
h1, h2, h3 {
  color: var(--gov-ink);
  letter-spacing: -0.025em;
}
h1 {
  font-weight: 750;
  padding-bottom: 0.25rem;
}
h2, h3 {
  font-weight: 680;
}
[data-testid="stMetric"] {
  background: var(--gov-surface);
  border: 1px solid var(--gov-border);
  border-radius: 14px;
  padding: 18px 20px;
  box-shadow: 0 3px 12px rgba(23,35,56,0.035);
  min-height: 112px;
}
[data-testid="stMetricLabel"] {
  color: var(--gov-muted);
  font-weight: 600;
}
[data-testid="stMetricValue"] {
  color: var(--gov-ink);
  font-weight: 750;
}
.stButton > button,
.stDownloadButton > button {
  border-radius: 9px;
  min-height: 42px;
  font-weight: 650;
  border: 1px solid #d7e0ed;
  transition: all 140ms ease-in-out;
}
.stButton > button[kind="primary"] {
  background: var(--gov-blue);
  border-color: var(--gov-blue);
  color: white;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
  border-color: var(--gov-blue);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(40,100,220,0.12);
}
[data-testid="stDataFrame"],
[data-testid="stTable"] {
  border: 1px solid var(--gov-border);
  border-radius: 11px;
  overflow: hidden;
  background: white;
}
[data-testid="stAlert"] {
  border-radius: 10px;
  border-width: 1px;
}
[data-testid="stExpander"] {
  border: 1px solid var(--gov-border);
  border-radius: 10px;
  background: white;
}
[data-testid="stTabs"] button {
  font-weight: 650;
}
input, textarea, [data-baseweb="select"] {
  border-radius: 8px !important;
}
hr {
  border-color: var(--gov-border);
  margin-top: 1.5rem;
  margin-bottom: 1.5rem;
}
@media (max-width: 768px) {
  [data-testid="stMainBlockContainer"] {
    padding: 1rem 0.8rem 2rem;
  }
  [data-testid="stMetric"] {
    padding: 13px;
    min-height: 90px;
  }
}
</style>
""", unsafe_allow_html=True)


POLICY_PATH = ROOT / "config" / "policy.json"
PORTFOLIO_PATH = ROOT / "data" / "synthetic_campaign_portfolio.json"
HISTORY_PATH = ROOT / "data" / "portfolio_assessments.json"
AUDIT_PATH = ROOT / "data" / "audit_ledger.json"
APPROVAL_PATH = ROOT / "data" / "human_approvals.json"
PLAYBOOK_PATH = ROOT / "data" / "campaign_guardian_playbooks.json"

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
            "Campaign Guardian",
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
    events = read_events(AUDIT_PATH)
    integrity = verify_chain_report(events)
    cols = st.columns(3)
    cols[0].metric("Ledger integrity", "VALID" if integrity["valid"] else "INVALID")
    cols[1].metric("Verified events", integrity["verified_count"])
    cols[2].metric("Latest sequence", integrity["event_count"])
    if integrity["valid"]:
        st.success(f"Hash chain verified. Head hash: {integrity['head_hash']}")
    else:
        st.error(
            f"Integrity check failed at sequence {integrity['first_invalid_sequence']}: "
            f"{integrity['reason']} Later appends remain blocked."
        )
    if events:
        st.dataframe(
            [{
                "Sequence": event.get("sequence"),
                "Timestamp": event.get("timestamp"),
                "Event": event.get("event_type"),
                "Campaign": event.get("campaign_id"),
                "Actor": event.get("actor"),
                "Hash": event.get("event_hash", "")[:16] + "…",
            } for event in reversed(events)],
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No audit events recorded yet. The empty ledger is valid.")
    st.download_button(
        "⬇ Download verified audit ledger JSON",
        json.dumps(export_ledger(AUDIT_PATH), indent=2),
        file_name="governance-audit-ledger.json",
        mime="application/json",
    )

elif page == "Campaign Guardian":
    st.caption("Evidence-led recommendations · deterministic compliance gate · human-controlled playbooks")
    st.info("Offline synthetic demonstration. Recommendations are never auto-applied. Quality scores cannot override compliance BLOCK.")
    scenario = st.selectbox(
        "Synthetic campaign scenario",
        ["Fully evidenced passing example", "Consent evidence missing", "Legal-basis evidence missing", "Known blocking example"],
    )
    scenario_file = "campaign-fail.json" if scenario == "Known blocking example" else "campaign-pass.json"
    evidence_col1, evidence_col2 = st.columns(2)
    consent_reference = evidence_col1.text_input(
        "Reviewer-provided synthetic consent reference",
        placeholder="SYNTHETIC-CONSENT-REF",
    )
    legal_basis_reference = evidence_col2.text_input(
        "Reviewer-provided synthetic legal-basis reference",
        placeholder="SYNTHETIC-LEGAL-REF",
    )
    st.caption("References are applied one at a time as candidate revisions, then re-evaluated. Use synthetic references only.")
    if st.button("Evaluate with Campaign Guardian", type="primary"):
        try:
            candidate = load_json(ROOT / "samples" / scenario_file)
            if scenario == "Consent evidence missing":
                candidate.pop("consent_evidence_ref", None)
            elif scenario == "Legal-basis evidence missing":
                candidate.pop("legal_basis_evidence_ref", None)
            references = {
                "consent_evidence_ref": consent_reference,
                "legal_basis_evidence_ref": legal_basis_reference,
            }
            improver = reviewer_evidence_improver(
                {field: value for field, value in references.items() if value.strip()}
            )
            result = run_bounded_improvement_loop(
                candidate, policy, improver=improver, max_iterations=MAX_ITERATIONS
            )
            st.session_state["campaign_guardian_result"] = result
            final = result["final_evaluation"]
            append_event(
                AUDIT_PATH, "CAMPAIGN_GUARDIAN_EVALUATED", final["campaign_id"],
                "DETERMINISTIC_GUARDIAN",
                {"decision": final["decision"], "quality_score": final["quality_score"],
                 "iterations": result["iteration_count"], "recommendations": len(final["recommendations"]["recommendations"])},
            )
        except (ValueError, OSError) as exc:
            st.error(str(exc))

    guardian_result = st.session_state.get("campaign_guardian_result")
    if guardian_result:
        final = guardian_result["final_evaluation"]
        cols = st.columns(3)
        cols[0].metric("Deterministic decision", final["decision"])
        cols[1].metric("Quality score", f"{final['quality_score']} / 100")
        cols[2].metric("Review cycles", guardian_result["iteration_count"])
        st.subheader("Bounded improvement loop")
        st.dataframe(guardian_result["iterations"], use_container_width=True, hide_index=True)
        st.caption("The quality score is descriptive only. Any failed or unknown mandatory invariant keeps the decision at BLOCK.")
        recommendations = final["recommendations"]["recommendations"]
        if recommendations:
            st.subheader("Evidence-based recommendations")
            st.dataframe(recommendations, use_container_width=True, hide_index=True)
            playbooks = read_playbooks(PLAYBOOK_PATH)
            active = playbooks["active_version"]
            st.write(f"Active playbook: {active}. Candidate versions do not alter deterministic policy.")
            pending = [v for v in playbooks["versions"] if v.get("status") == "PENDING_REVIEW"]
            if not pending and st.button("Create candidate playbook version"):
                try:
                    created = create_candidate_playbook(PLAYBOOK_PATH, recommendations)
                    st.success(f"Candidate {created['version']} is pending human review. The active version remains unchanged.")
                    st.rerun()
                except (ValueError, OSError) as exc:
                    st.error(str(exc))
            if pending:
                candidate_version = pending[0]["version"]
                candidate = pending[0]
                active_playbook = next(
                    version for version in playbooks["versions"]
                    if version.get("version") == playbooks["active_version"]
                )
                diff = playbook_diff(active_playbook, candidate)
                st.subheader("Changes from active playbook")
                st.caption(f"{diff['from_version']} → {diff['to_version']}")
                if diff["invariants_unchanged"]:
                    st.success("Mandatory invariants are unchanged.")
                else:
                    st.warning("Invariant metadata differs; mandatory controls are still checked before review.")
                diff_cols = st.columns(3)
                diff_cols[0].metric("Added recommendations", len(diff["added"]))
                diff_cols[1].metric("Removed recommendations", len(diff["removed"]))
                diff_cols[2].metric("Unchanged recommendations", diff["unchanged_count"])
                if diff["added"]:
                    with st.expander("Show added recommendations"):
                        st.json(diff["added"])
                if diff["removed"]:
                    with st.expander("Show removed recommendations"):
                        st.json(diff["removed"])
                st.subheader(f"Review candidate playbook {candidate_version}")
                with st.form("campaign_guardian_playbook_review"):
                    reviewer = st.text_input("Human reviewer identity")
                    action = st.radio("Decision", ["APPROVE", "REJECT"], horizontal=True)
                    rationale = st.text_area("Review rationale (required)")
                    explicit = st.checkbox("I explicitly approve activating this candidate", disabled=action != "APPROVE")
                    submitted = st.form_submit_button("Record human decision")
                if submitted:
                    try:
                        review_candidate_playbook(
                            PLAYBOOK_PATH, AUDIT_PATH, candidate_version, reviewer, action, rationale,
                            explicit_human_approval=explicit,
                        )
                        st.success("Human decision recorded in the hash-chained audit ledger.")
                        st.rerun()
                    except (ValueError, OSError) as exc:
                        st.error(str(exc))
        else:
            st.success("No recommendations were generated; all evaluated checks passed.")
    playbooks = read_playbooks(PLAYBOOK_PATH)
    st.subheader("Playbook version history")
    st.dataframe(playbooks["versions"], use_container_width=True, hide_index=True)
    st.caption("Activation is a human review action. This feature never deploys, sends, or executes a campaign.")

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
