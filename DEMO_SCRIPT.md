# Demo Video Script

Target duration: 5 minutes.

## 0:00-0:45 Architecture

- Show `ARCHITECTURE_PLAN.md`.
- Explain the platform layers:
  - frontend chat/dashboard
  - backend agent
  - tool layer
  - access control
  - model router
  - data store
  - enterprise-scale roadmap

## 0:45-2:00 Customer Chat

- Select `Northstar Customer`.
- Ask:

```text
Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.
```

- Show:
  - order lookup
  - document search
  - calculation
  - citations
  - confidence
  - model route

## 2:00-2:45 Access Control

- Keep `Northstar Customer` selected.
- Ask:

```text
Can I see LumenWorks order ORD-2002?
```

- Show that the backend authorization guard blocks access.

## 2:45-3:45 Internal Support Workflow

- Select `ParcelPilot Support Agent`.
- Ask:

```text
Escalate ticket TKT-501 because it is high severity and near SLA breach.
```

- Show that the agent prepares an escalation but does not execute it.
- Confirm the action.
- Show created escalation.

## 3:45-4:30 Proactive Dashboard

- Open Issue Dashboard.
- Show SLA risk queue and recurring issue groups.

## 4:30-5:00 Decisions

- Explain:
  - source reliability ranking
  - tool-layer access control
  - confirmation before actions
  - OpenAI/Hugging Face/local model routing
  - enterprise scalability path
