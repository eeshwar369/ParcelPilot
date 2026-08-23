# UI Revamp Note

The interface is now implemented as a Next.js frontend split into a customer-facing portal and a separate internal admin console.

## Key Changes

- `frontend/app/page.tsx` is a customer portal with a floating account-scoped support widget.
- `frontend/app/admin/page.tsx` is a separate internal operations console.
- Customer users do not see internal traces, cross-account dashboard data, or admin controls.
- Admin users get prompt testing, tool traces, sources, model routes, dashboard, and confirmed actions.
- Data refresh uses a toast instead of polluting the chat.
- The layout avoids horizontal overflow and clamps long source excerpts.

## Built-In Test Scenarios

The admin console includes one-click scenarios for:

- Northstar cancellation
- LumenWorks service credit
- Cross-account privacy
- Internal SLA risk
- Confirmed escalation
- Known issue check
- Contract override
- Read-only action guard

More prompts are listed in [SAMPLE_PROMPTS.md](SAMPLE_PROMPTS.md).
