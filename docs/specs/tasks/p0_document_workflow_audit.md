# P0 Audit: Document Workflow Audit (Input to Implementation)

Status: Required pre-implementation  
Date: 2026-05-29  
Owner: Product + Operations + Frontend

## Purpose

Capture factual baseline for document-to-field manual entry workflow before implementation.

## Collect

1. Most frequently opened document types.
2. Most frequently copied fields per document type.
3. Current click/step count for core scenarios.
4. Where operators lose time (switching, searching, zooming, scrolling).
5. Which roles are most impacted.

## Technical Discovery (Required Before Design)

1. Where documents are physically stored and served from.
2. How documents are opened today (inline/new tab/download).
3. PDF behavior today (embedded vs external tab).
4. Image behavior today (embedded vs download/open external).
5. Size/performance limits that affect preview.

## Minimum Output Table

| Scenario | Document Type | Fields Filled | Current Steps | Tab Switches | Pain Notes |
|---|---|---|---:|---:|---|
| Candidate data entry | Passport | Name, number, expiry |  |  |  |
| Candidate data entry | Driver license | Number, expiry, categories |  |  |  |

## Decision Use

Results become direct input for:

- `p0_document_workspace.md`

No implementation starts until this audit has baseline data.

## Design Hypotheses to Validate

Hypothesis A (preferred first):

- `Workspace Mode` with explicit action (`Open Workspace`),
- split working layout (document + form),
- baseline card remains unchanged outside this mode.

Hypothesis B:

- embedded workspace in right column.

## Mandatory Comparison Output

For both hypotheses, document:

1. document visible width,
2. form visible width,
3. additional scroll load,
4. click reduction vs current flow,
5. operator preference from quick trial.
