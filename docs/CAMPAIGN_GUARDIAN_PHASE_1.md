# Campaign Guardian Phase 1

## Architecture

Campaign Guardian extends the current Governance OS without replacing its QA engine or dashboard. The deterministic QA engine produces rule-level evidence. The Guardian recommendation writer maps non-PASS findings to fixed, evidence-specific next steps and never edits campaign data. The evaluator derives the compliance gate from the QA result and verifies mandatory invariants independently of the quality score.

A local bounded loop can re-evaluate a proposed synthetic campaign after each optional callback result. The loop accepts no more than five cycles, makes no model or network call, and does not approve recommendations. A candidate playbook version stores recommendation guidance and an immutable copy of the mandatory invariants. It stays pending until a human reviewer explicitly approves or rejects it. Activation and rejection are written to the existing SHA-256 hash-chained audit ledger.

The Streamlit UI adds a Campaign Guardian section to the existing Governance OS navigation. It exposes bundled synthetic scenarios, deterministic results, evidence-linked recommendations, candidate creation, and a human review form. No separate dashboard is created.

## Phase 1 acceptance criteria

1. Recommendations cite the QA rule, status, and evidence fact that produced them.
2. The evaluator uses deterministic QA and returns its own decision, invariant errors, and descriptive quality score.
3. The improvement loop rejects limits above five and never exceeds five evaluations.
4. Candidate playbooks have numbered versions and explicit pending, active, superseded, or rejected status.
5. Mandatory rules and safety invariants are fixed in code and candidate weakening is rejected.
6. Synthetic golden scenarios cover passing, missing-consent, missing-legal-basis, and invalid-consent cases.
7. Guardian evaluations and playbook reviews integrate with the existing hash-chained audit ledger.
8. Human approval and rejection are available inside the existing Streamlit application.
9. Missing consent evidence or legal-basis evidence produces BLOCK.
10. Quality scores cannot compensate for a failed or unknown mandatory control.
11. AI and system actor labels cannot approve recommendations; activation requires explicit human approval.
12. The feature uses synthetic examples only and includes no campaign execution, deployment, external LLM, paid API, or live Adobe/Salesforce integration.

## Invariant behavior

The deterministic gate requires every mandatory rule to be PASS. Mandatory rules include consent evidence (CON-001), legal-basis evidence (CON-002), suppression integrity (SUP-001), typology activation (TYP-001), and proof approval (APR-001). A missing or non-synthetic evidence reference is UNKNOWN and therefore blocks. Existing non-PASS checks also preserve the existing fail-closed behavior.

The quality score counts PASS checks as a percentage. It is never used to set or relax the decision. The Guardian loop does not automatically modify campaigns. The active playbook remains unchanged while a candidate is pending or rejected.

## Storage and audit

Candidate version history is stored in data/campaign_guardian_playbooks.json when the user creates a candidate in the UI. No file is created merely by opening the page. Version changes use atomic replacement. Guardian assessment and human playbook decisions append to data/audit_ledger.json through the existing audit module. If the ledger fails chain verification, the audit append is refused before the playbook store is updated.

## Tests and local use

Run all tests with:

    PYTHONPATH=src pytest -v

Run the Governance OS with:

    pip install -r requirements.txt
    streamlit run streamlit_app.py

The bundled passing example includes synthetic consent and legal-basis evidence references. The Guardian regression fixture is tests/fixtures/campaign_guardian_golden.json.

## Limitations

Recommendations are fixed rule-based guidance, not verified root-cause analysis. The Streamlit UI exposes reviewer-entered synthetic consent and legal-basis references. The callback applies only missing references one at a time, without overwriting existing values, then reruns deterministic evaluation. It never invents evidence and stops within five evaluations. Reviewer identity is self-asserted in this prototype. Local JSON persistence has no multi-user transaction, authentication, or access control. Hash chaining is tamper-evident but cannot prevent a privileged administrator from rewriting and rehashing the entire ledger. Playbook activation governs recommendation guidance only; it does not modify the active deterministic policy or authorize campaign release.
