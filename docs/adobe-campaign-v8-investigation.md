# Adobe Campaign v8 – Generic Governance Baseline

## Purpose and scope

This document describes a generic governance perspective for Adobe Campaign Classic v8. It is not a description of any employer, customer, tenant, market, or production implementation.

Capabilities and deployment characteristics can vary by offering, release, configuration, and contractual setup. Confirm technical details against current Adobe Experience League documentation and the target environment.

## Architecture areas to validate

- **Deployment model**: Confirm the applicable supported deployment arrangement.
- **Data architecture**: Validate the configured database and federated data access model.
- **Delivery routing**: Confirm delivery topology and where execution and status updates occur.
- **Asynchronous processing**: Identify provisional statuses and authoritative terminal outcomes.
- **Performance and scale**: Use tenant-specific capacity guidance. Do not assume generic throughput figures are production guarantees.

## Interfaces and operations

- Identify supported client and web interfaces for the installed release.
- Map operator, developer, administrator, and approver responsibilities.
- Validate workflow monitoring, audit evidence, permissions, and approval capabilities.

## Governance capabilities to assess

- Typology and delivery rules.
- Pressure, fatigue, and contact policy controls where configured.
- Workflow readiness and dependency validation.
- Personalization and content validation.
- Approval and audit evidence.
- Access control and separation of duties.

Confirm availability and behavior in the target release and configuration.

## Limitations and compatibility

Do not assume a feature available in one Campaign release or deployment model is available in another. Assess migration, integrations, and compatibility using applicable official documentation.

## Positioning with journey orchestration

Select and integrate products based on documented requirements, event latency, data architecture, channel needs, and operational ownership.

## Implications for governed AI

- **Deterministic validation** evaluates mandatory rules and produces machine-readable evidence.
- **AI-assisted investigation** summarizes evidence, identifies anomalies, and proposes diagnostic steps.
- **Human approval** remains explicit for decisions requiring authorized judgment.
- **Fail-closed handling** prevents missing, provisional, or ambiguous evidence from being treated as success.
- **Auditability** records rule outcomes, evidence references, timestamps, and authorized overrides.

### Critical design rule

Treat unknown, pending, or non-terminal delivery states as **unknown**, not success. Define terminal states and timeout behavior using the actual delivery topology. Never infer successful delivery from the absence of an error.

## Verification checklist

1. Confirm the deployment model and release.
2. Validate architecture against official documentation.
3. Map checks to supported data sources and interfaces.
4. Establish policy-owned thresholds and timeout values.
5. Test unknown, failure, retry, and override paths in a non-production environment.

## Sources

Consult current Adobe Experience League documentation, release notes, and deployment-specific technical guidance. This document intentionally avoids fixed performance claims and unverified tenant assumptions.
