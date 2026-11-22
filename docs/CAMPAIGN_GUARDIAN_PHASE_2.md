# Campaign Guardian Phase 2 — free governance hardening

Phase 2 keeps the existing Streamlit Governance OS, deterministic evaluator, synthetic examples, and local JSON storage. It adds clearer evidence for reviewing local audit and candidate playbook state without adding a service or changing campaign decision authority.

## Changes

- The Audit Ledger page reports whether the current hash chain is valid, how many events were verified, the latest sequence, and the first invalid event with a reason.
- The JSON export includes the events and the verification result captured at export time.
- Candidate playbook review shows added and removed recommendations and whether its invariant metadata matches the active version before the reviewer chooses approve or reject.
- Regression tests cover audit tampering, missing/reordered events, export metadata, playbook comparison, invariant weakening, and rejection retention.

## Guarantees and limitations

The hash chain detects event edits, deletions, insertions, and reordering while the original chain remains intact. It does not stop an administrator from rewriting and rehashing the entire local JSON file. The export is a review aid, not a digital signature or immutable archive. Streamlit-hosted JSON persistence can be lost on restart, and reviewer identity remains self-entered. Keep using synthetic data only and download exports when you need a copy.

This phase adds no paid APIs, database, authentication service, external LLM, Adobe/Salesforce connection, campaign execution, or deployment behavior. It does not change the deterministic APPROVE/BLOCK result or activate a playbook without the existing explicit human approval.

## Run locally

    pip install -r requirements.txt
    PYTHONPATH=src pytest -q
    streamlit run streamlit_app.py
