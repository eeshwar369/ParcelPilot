# Product Note

## Additional Client Problem Chosen

I chose proactive SLA and escalation management for logistics support teams. ParcelPilot does not only answer customer questions; it also surfaces high-risk tickets, SLA pressure, recurring issue patterns, and escalation queues for internal operators.

## How It Is Addressed

The customer assistant answers shipment, agreement, cancellation, and support-policy questions with source-backed responses. If a request needs human judgment or policy-restricted action, the assistant prepares an escalation instead of pretending to resolve it. The admin dashboard lets operations users review escalated tickets, verify them, and respond.

## What Else I Would Build

Next steps would include production SSO/RBAC, audit-log search, ticket-system integrations, carrier webhook ingestion, background document ingestion workers, customer notifications, and evaluation dashboards for answer quality and escalation accuracy.

## Intentionally Left Out

I intentionally left out full enterprise SSO, a complete ticketing-system sync, payment-grade billing workflows, and long-running background worker orchestration. The submitted version focuses on the core AI support loop, source trust, confirmed actions, and deployable architecture.

## Success Metric

Primary metric: percentage of eligible support questions resolved with a high-confidence, source-backed answer without human escalation, while keeping incorrect-policy-answer rate below an agreed threshold.
