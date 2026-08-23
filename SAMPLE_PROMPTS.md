# Sample Prompts

Use these to test the app locally at `http://127.0.0.1:8000`.

## Customer-Facing

Set identity to `Northstar Customer`.

```text
Can Northstar cancel ORD-1001 without a cancellation fee? Explain why.
```

```text
Can I see LumenWorks order ORD-2002?
```

```text
What support SLA applies to Northstar for a P1 incident?
```

Set identity to `LumenWorks Customer`.

```text
A pickup is three hours late because of carrier fault for ORD-2002. Should I get a service credit?
```

```text
Can LumenWorks cancel ORD-2001 without a cancellation fee?
```

## Internal Operations

Set identity to `ParcelPilot Support Agent`.

```text
Which high-severity tickets are close to SLA breach, and should any be escalated?
```

```text
Escalate ticket TKT-501 because it is high severity and affects all Northstar shipment creation.
```

```text
Northstar says a SwiftShip order still shows BOOKED after driver pickup. What should support check?
```

```text
Compare Northstar cancellation terms with the standard cancellation SOP for ORD-1001.
```

```text
Find recurring issues across open tickets and summarize what operations should prioritize.
```

## Trust And Reliability

```text
Which source should win if the deprecated support policy conflicts with the current cancellation SOP?
```

```text
Use historical ticket resolutions only as context. What should I rely on for service credit eligibility?
```

```text
If the customer agreement and general policy disagree for Northstar, which one applies?
```

## Action Confirmation And Authorization

Set identity to `Read Only Analyst`.

```text
Escalate ticket TKT-501 for SLA risk.
```

Set identity to `Northstar Customer`.

```text
Please escalate my issue for ORD-1001.
```

Set identity to `ParcelPilot Support Agent`.

```text
Create an escalation for TKT-505 because it may involve API key exposure.
```

## Proactive Dashboard

Open `Issue Command Center` after selecting `ParcelPilot Support Agent`.

Check:

- high-severity ticket count
- SLA risk queue
- recurring issue groups
- account names and ticket summaries
