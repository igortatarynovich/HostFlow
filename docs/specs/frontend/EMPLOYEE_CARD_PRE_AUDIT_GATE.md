# EMPLOYEE_CARD_PRE_AUDIT_GATE

Status: Mandatory before Employee Card audit  
Date: 2026-05-29  
Owner: Product + Frontend + Domain Owners

## Purpose

Prevent non-necessary redesign work by proving business need before opening Employee Card audit.

This gate enforces project axiom:

- `Do not improve a benchmark without a proven problem.`

## Gate Questions (Required)

Answer all five questions with concrete evidence.

### 1) Who uses Employee Card?

List actual user groups (not assumptions), for example:

- HR
- Recruiter
- Operations
- Fleet
- Compliance

Required output:

- primary users,
- secondary users,
- owner of workflow decisions in this card.

### 2) What are the 5 most frequent actions in this card?

Examples:

- document check,
- expiry review,
- status update,
- renewal initiation,
- history review.

Required output:

- top-5 action list,
- approximate frequency or rank.

### 3) What real pains are already known?

Facts only. Examples:

- hard to find Code95 expiry,
- medical checks are missed,
- users must open multiple tabs for core operation.

Required output:

- pain list with source (ticket/interview/ops report),
- explicit statement if no pain is known.

### 4) What metrics, incidents, or errors exist?

Examples:

- overdue documents,
- missed reminders,
- HR operational errors.

Required output:

- metric list with period,
- incident examples (if available),
- trend direction (stable/worse/better).

### 5) Is there proof this screen blocks work?

Answer strictly:

- `Yes` or `No`.

Required output:

- short evidence summary for answer.

## Decision Logic

### Result: PASS

Condition:

- real pains are confirmed,
- and/or measurable losses/errors exist,
- and there is proof that Employee Card structure/flow contributes to those losses.

Action:

- open `Employee Card Audit` branch,
- run full audit under `OPERATIONAL_CARD_AUDIT_PROGRAM.md`.

### Result: NO BUSINESS CASE

Condition:

- no proven pain,
- no measurable loss,
- no evidence that current screen blocks core work.

Action:

- classify Employee Card as current baseline,
- do not open redesign/audit branch,
- revisit only when new evidence appears.

## Output Template

Use this format:

```md
## Employee Card Pre-Audit Gate Result

1. Users:
- ...

2. Top-5 Actions:
- ...

3. Known Pains:
- ...

4. Metrics/Incidents:
- ...

5. Proof of Work Block:
- Yes/No
- Evidence: ...

Final Decision:
- PASS / NO BUSINESS CASE

Decision Owner:
- ...

Date:
- YYYY-MM-DD
```
