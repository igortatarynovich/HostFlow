# P0 Task: Document Workspace + Data Entry

Status: Planned  
Priority: P0  
Owner: Frontend + Product  
Date: 2026-05-29

## Execution Order Constraint

Implementation starts only after:

1. `p0_document_workflow_audit.md` is completed,
2. document workspace prototype is reviewed.

## Problem

Operator must switch between document view and form fields to copy data manually.
This causes repeated context switching and slower processing.

## Goal

Reduce document/form switching to zero during manual entry.

## Scope

- embedded document workspace inside card,
- support PDF and images,
- zoom controls,
- switch between uploaded documents,
- document remains visible while fields are being filled,
- no OCR,
- no AI suggestions,
- no autofill.

## Target Workflow

Document panel (left) + form panel (right):

1. view document,
2. enter data into fields,
3. switch to next document without opening new tabs.

Preferred first hypothesis is `Workspace Mode` (on-demand split mode), not permanent right-column embedding:

- card stays structurally unchanged,
- operator clicks `Open Workspace`,
- screen switches to split working mode,
- document area gets enough width for readable PDF/image,
- operator keeps form editing context.

## Prototype Variants (Mandatory)

Before implementation, compare two variants:

1. `Workspace Mode` (split working mode, toggle on/off)
2. `Right Column Embedded Workspace`

## Variant Evaluation Criteria

1. Document readable area (passport/license readability without excessive zoom).
2. Form usable area (field visibility and edit speed).
3. Extra scroll introduced by layout.
4. Click count reduction vs current flow.
5. Context preservation (no disruption of baseline card workflow).

## Baseline Protection Rule

Candidate Card baseline layout is preserved.
Document Workspace is an operational mode, not a baseline card redesign.

## Out of Scope

- automatic extraction,
- semi-automatic extraction,
- scanner quality improvements,
- candidate card structural redesign.

## Acceptance Criteria

1. Operator can keep document visible and editable form visible at the same time.
2. No browser tab switching is required for core data-entry flow.
3. PDF and image rendering works in the same workspace pattern.
4. Zoom is available and usable for small text.
5. Switching between candidate documents does not reset current form context.

## Dependencies

- existing document upload/storage pipeline,
- current candidate/employee data-entry forms.

## Input Audit Required Before Build

- `docs/specs/tasks/p0_document_workflow_audit.md`
