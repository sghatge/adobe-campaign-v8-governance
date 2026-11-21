# Adobe Campaign v8 – Governance Baseline (Revised Nov 2026)

## Overview

Adobe Campaign v8 (Managed Cloud Services) is the long-term evolution of Campaign Classic. It is optimized for enterprise-scale batch campaigns and retains most of the depth power users expect from Classic, while moving to a fully managed cloud architecture.

## Key Architectural Facts

- **Deployment model**: Managed Cloud Services only (no on-premise or hybrid).
- **Database**: Hybrid architecture. Enterprise (FFDA) uses Snowflake as the cloud database for batch execution + local Campaign DB for real-time/UI operations.
- **Full Federated Data Access (FFDA)**: Most data lives remotely; simplifies maintenance (indexing burden shifts to managed cloud DB; Campaign-side index maintenance is greatly reduced).
- **Mid-sourcing**: Default and required delivery path in Managed Cloud. Internal routing is disabled. Delivery status updates are **asynchronous**.
- **Performance (Enterprise/FFDA)**:
  - Up to 20 million operations per hour (batch).
  - Up to 1 million messages per hour (transactional).
  - Audience building measured in minutes rather than hours.

## Interfaces

- **Client Console**: Still the primary power-user, developer, and admin interface.
- **Campaign Web User Interface**: Modern browser UI (via Adobe CX Enterprise). Rapidly expanding feature set but still has gaps in advanced admin/approval workflows.

## Strengths Relevant to Governance

- Strong typology rules, fatigue/pressure rules, and approval workflows.
- Robust audit logging potential.
- Advanced personalization and workflow engine.
- Native AI Assistant / Generate Content (text + image) with brand controls.
- Clear separation between deterministic execution controls and probabilistic AI assistance.

## Limitations / Changes from Classic v7

- No on-premise or hybrid deployment.
- Some Classic features unavailable or limited under FFDA (MRM, Coupons, Web tracking, Surveys).
- Removed: Social marketing with Facebook, ACS Connector, LDAP, native username/password login (auth moved to IMS/SSO).
- Automated migration tooling from existing v7 environments is not yet available.

## Positioning vs Adobe Journey Optimizer

Campaign v8 remains the platform of choice for complex, high-volume, batch-centric, multi-wave campaigns.

Journey Optimizer is the preferred tool for real-time, event-driven, 1:1 journeys.

Many enterprises run both and integrate them.

## Implications for Governed Agentic AI

The architecture of Campaign v8 makes external governance layers more valuable, not less:

- **Deterministic Pre-Flight Gate** can sit on top of typology, fatigue, approval, and validation mechanisms.
- **AI-Assisted Investigation layer** can leverage both native Generate Content capabilities and external agentic skills.
- **Human-in-the-loop patterns** (In the Loop / On the Loop / Out of the Loop) map cleanly to existing approval and dual-control concepts.
- **Fail-closed timeout logic and mandatory override logging** become critical safety controls in a managed-cloud environment.

### Critical Design Rule for Agentic Systems

Because delivery status updates are **asynchronous** in the mid-sourcing model, agents must never interpret a non-final status as success. Any agent reading delivery status must treat `pending` or `not-yet-updated` status as `unknown`, not `success`. Fail-closed timeout logic is required.

## Sources

- Adobe Experience League documentation (Campaign v8, last updated November 2026)
- Official transition guides (v7 → v8)
- Product release notes and FAQ (as of November 2026)
