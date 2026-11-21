# Pre-Flight Gate Checklist: Adobe Campaign v8

This checklist maps deterministic governance rules to Adobe Campaign v8 capabilities. It is designed for both human operators and agentic enforcement.

## 1. Audience & Targeting Integrity

| Check | Rule | Agentic Logic | Failure Action |
|-------|------|---------------|----------------|
| **Baseline Drift** | Audience size must be within ±15% of historical average for similar segments. | Compare current query count vs. last 3 sends of same type. | **FAIL-CLOSED**: Block send. Require human override. |
| **Suppression Integrity** | Global suppression list (GSL) and custom exclusions must be applied. | Verify `exclusion` workflow steps are active and linked. | **FAIL-CLOSED**: Block send. |
| **Consent & Opt-Out** | No records with `optOut = true` or missing consent flags. | Query target table for consent status. Count violations. | **FAIL-CLOSED**: Block send if >0 violations. |
| **Fatigue Rules** | Contact frequency must not exceed defined pressure rules (e.g., 2 emails/week). | Check `nms:profile` fatigue counters against typology rules. | **WARN**: Flag for review if >90% threshold. |

## 2. Content & Personalization

| Check | Rule | Agentic Logic | Failure Action |
|-------|------|---------------|----------------|
| **Personalization Mapping** | All `<%= %>` tags must resolve to valid schema fields. | Parse HTML content. Validate field existence in target schema. | **FAIL-CLOSED**: Block send. |
| **Link Verification** | All URLs must be valid, tracked, and contain UTM parameters. | Extract hrefs. Check for broken links. Verify UTM structure. | **WARN**: Flag broken links. Block if >5% broken. |
| **Mirror Page** | Mirror page link must be present and functional. | Check for `mirrorPage` tag. Test URL resolution. | **FAIL-CLOSED**: Block send. |
| **Subject Line** | Must not contain spam-trigger words or excessive caps. | NLP scan against spam keyword list. | **WARN**: Flag for human review. |

## 3. Technical & Workflow Readiness

| Check | Rule | Agentic Logic | Failure Action |
|-------|------|---------------|----------------|
| **Workflow Status** | Upstream workflows (data extraction, enrichment) must be `Finished`. | Check workflow instance status via API. | **FAIL-CLOSED**: Block send. |
| **Send Time Validation** | Send time must be in valid ISO/IANA format and within business hours. | Validate timezone offset. Check against allowed send windows. | **FAIL-CLOSED**: Block send. |
| **Typology Rules** | All mandatory typology rules (control groups, capacity) must be active. | Verify typology rule binding in delivery properties. | **FAIL-CLOSED**: Block send. |

## 4. Async Mid-Sourcing Governance (Critical)

| Check | Rule | Agentic Logic | Failure Action |
|-------|------|---------------|----------------|
| **Delivery Status** | Treat `pending` or `in-progress` as `unknown`. | Do not assume success until `sent` or `delivered` status is confirmed via async callback. | **FAIL-CLOSED**: Timeout after 15 mins. Alert ops team. |
| **Override Logging** | Any human override of a FAIL-CLOSED rule must be logged. | Require written justification in audit log. | **MANDATORY**: Log timestamp, user, and reason. |

## Implementation Notes

- **Fail-Closed**: If any check fails, the delivery is blocked automatically.
- **Human Override**: Only authorized users can override a block. Overrides are logged in the `audit_log` table.
- **Async Status**: Due to mid-sourcing, delivery status updates are asynchronous. Agents must poll or wait for callbacks. Never assume immediate success.
