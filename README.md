# Adobe Campaign v8 Governance

An independent, generic reference project for governance patterns in Adobe Campaign Classic v8 environments.

This repository contains an architecture discussion and a configurable pre-flight checklist. It uses no customer, employer, market, campaign, recipient, or production data.

## Contents
- [Architecture and Governance Baseline](docs/adobe-campaign-v8-investigation.md)
- [Pre-Flight Gate Checklist](docs/pre-flight-checklist.md)

## Governance approach

**Deterministic controls enforce what must be true. AI investigates, contextualizes, and recommends. Authorized humans retain approval authority.**

The reference model separates:
1. **Deterministic Pre-Flight Gate** — explicit validation rules and fail-closed handling.
2. **AI-Assisted Investigation** — evidence-based explanations and diagnostic suggestions that cannot bypass mandatory controls.

## Safe-use boundaries

- Treat all examples and thresholds as illustrative.
- Do not add employer, customer, tenant, market, campaign, recipient, or confidential operational information.
- Validate product capabilities against current Adobe documentation and the intended deployment.
- This project is independent and is not affiliated with or endorsed by Adobe.

## Suggested use

1. Review the baseline against official product documentation.
2. Map controls to the intended environment.
3. Configure thresholds, evidence requirements, and timeout behavior through an approved policy.
4. Test fail-closed paths in a non-production environment.

## Topics

Adobe Campaign Classic v8 · CRM Operations · Campaign Governance · Agentic AI · Human-in-the-Loop
