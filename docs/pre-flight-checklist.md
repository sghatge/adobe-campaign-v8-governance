# Pre-Flight Gate Checklist: Adobe Campaign v8

A generic, configurable checklist for campaign readiness. It contains no customer, employer, tenant, market, campaign, recipient, or production data.

All thresholds, field mappings, and enforcement actions must be defined and approved by the owner of the target environment.

## 1. Audience and targeting integrity

| Check | Rule to configure | Validation approach | Example failure action |
|---|---|---|---|
| Audience variance | Define an approved variance threshold. | Compare current audience count with an approved historical baseline. | Block or require review according to policy. |
| Suppression integrity | Required exclusions must be applied. | Verify suppression inputs and exclusion logic. | Block if mandatory exclusions are absent. |
| Consent and opt-out | Consent must be valid for the intended purpose and channel. | Validate consent evidence against the approved data model. | Block when consent is missing or withdrawn. |
| Contact policy | Apply the configured frequency and fatigue policy. | Evaluate contact history against approved policy. | Warn or block according to policy. |

## 2. Content and personalization

| Check | Rule to configure | Validation approach | Example failure action |
|---|---|---|---|
| Personalization mapping | Every expression must resolve to an approved field or function. | Validate referenced fields against the target schema. | Block unresolved references. |
| Link verification | Links must meet approved destination and tracking policy. | Validate destinations and tracking rules. | Warn or block according to policy. |
| Mirror page | Include and validate when required. | Confirm the required element and test resolution. | Block when mandatory functionality is absent. |
| Content quality | Apply approved content and deliverability checks. | Run deterministic checks and authorized review. | Warn or require review. |

## 3. Technical and workflow readiness

| Check | Rule to configure | Validation approach | Example failure action |
|---|---|---|---|
| Workflow status | Required workflows must reach an approved success state. | Inspect supported workflow status and evidence. | Block when failed, running, or unknown. |
| Send-time validation | Use an approved time zone and deployment window. | Validate timestamp and policy window. | Block invalid schedules. |
| Typology and delivery rules | Required controls must be active. | Verify rules and their bindings. | Block when mandatory controls are inactive. |
| Approval | Required approvals must be recorded. | Verify approval identity, state, and evidence. | Block when approval is absent. |

## 4. Asynchronous delivery governance

| Check | Rule to configure | Validation approach | Example failure action |
|---|---|---|---|
| Delivery status | Provisional or non-terminal statuses are unknown. | Confirm status against authoritative delivery evidence. | Retain block until a valid terminal state. |
| Timeout | Define a timeout for the actual delivery topology. | Measure elapsed time from the documented transition. | Escalate; do not auto-approve. |
| Override logging | Every authorized override needs a reason and evidence. | Record actor, timestamp, rule, reason, and approval reference. | Reject unauthorized or incomplete overrides. |

## Implementation notes

- **Fail-closed**: A failed or unknown mandatory control must not be interpreted as approval.
- **Human override**: Permit only explicitly authorized roles under documented policy.
- **Evidence**: Retain inputs, rule version, result, timestamp, and evidence references.
- **Configuration**: Keep thresholds and timeout values in reviewed configuration, not hard-coded assumptions.
- **Testing**: Exercise pass, fail, unknown, retry, and override scenarios in a non-production environment.

This checklist is a design aid, not a production control or a claim of native Adobe Campaign functionality.
