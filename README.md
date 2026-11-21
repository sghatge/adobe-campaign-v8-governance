# Adobe Campaign v8 Governance

A practical governance baseline for enterprise campaign operations on Adobe Campaign Classic v8 (Managed Cloud Services).

This repository brings together an architecture investigation and a deterministic pre-flight checklist for campaign readiness, with a focus on governed agentic AI.

## Contents

- [Adobe Campaign v8 – Governance Baseline](docs/adobe-campaign-v8-investigation.md)
- [Pre-Flight Gate Checklist](docs/pre-flight-checklist.md)

## Governance approach

**Deterministic controls enforce what must be true. AI investigates, contextualizes, and recommends. Humans retain explicit approval authority.**

The proposed two-layer model separates:

1. **Deterministic Pre-Flight Gate** — non-negotiable validation and fail-closed controls.
2. **AI-Assisted Investigation** — root-cause analysis, cross-system anomaly investigation, and evidence-backed reporting.

## Important scope note

The documents in this repository are a working governance baseline supplied for this project. They are not a substitute for current Adobe product documentation, tenant-specific architecture validation, or formal operational approval. Verify product capabilities, performance figures, deployment constraints, and implementation details against current Adobe Experience League documentation and the applicable customer environment before using them for production decisions.

## Suggested use

1. Review the architecture baseline with the Adobe Campaign platform owner.
2. Map each checklist control to the actual schemas, workflows, typologies, APIs, and approval model in the target environment.
3. Define evidence requirements, thresholds, timeout behavior, and authorized override roles.
4. Test all fail-closed paths in a non-production environment before enabling enforcement.

## Topics

Adobe Campaign Classic v8 · CRM Operations · Campaign Governance · Agentic AI · Human-in-the-Loop · Marketing Automation
