# Product Note

## Chosen Additional Client Problem

The primary additional problem addressed is **Trust and Reliability**.

ParcelPilot's source base is imperfect: older policies may be deprecated, customer agreements may override general policy, and historical ticket resolutions can contain wrong guidance. The product therefore cannot behave like a generic chatbot that treats every retrieved chunk as equally true.

## How The Product Addresses It

- Uses source authority ranking:
  - customer agreement
  - current SOP
  - current support policy
  - operations guide
  - structured operational data
  - historical tickets
  - deprecated policy
- Enforces customer/account access in the tool layer.
- Shows tool traces and sources in the UI.
- Returns confidence levels.
- Escalates low-confidence or conflicting cases.
- Requires confirmation before any state-changing action.
- Logs model/provider choices and cost estimates.

## Additional Problem Also Included

The product includes a lightweight version of **Proactive Issue Detection** through the internal dashboard.

The dashboard highlights:

- high-severity tickets
- SLA-risk tickets
- recurring issue groups
- account impact

## What I Would Build Next

Priority 1:

- Human review queue for disputed, low-confidence, or high-impact answers.

Priority 2:

- Full ingestion pipeline for production document versioning and effective dates.

Priority 3:

- CRM/ticketing integrations such as Zendesk, Intercom, Salesforce, Slack, and Jira.

Priority 4:

- Enterprise tenant admin console with SSO, SCIM, quotas, retention, and audit exports.

Priority 5:

- Advanced anomaly detection and root-cause clustering across tickets, carriers, accounts, and routes.

## Intentionally Left Out Of The First Build

- Real SSO/SAML/OIDC.
- Real carrier API integrations.
- Real payment/billing workflows.
- Automatic refunds or service-credit execution.
- Production Kubernetes manifests.
- Full SOC 2 evidence workflows.
- Dedicated vector database.

These are included in the architecture plan as the enterprise roadmap, but the first implementation focuses on the core support-agent loop.

## Success Metric

Primary metric:

- **Correct containment rate:** percentage of requests resolved by the AI without later human rework.

Supporting metrics:

- average time to resolution
- escalation precision
- low-confidence rate
- citation acceptance rate
- unauthorized data exposure rate, target zero
- OpenAI cost per resolved conversation
