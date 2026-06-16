# P0 Task: UI Translation Cleanup

Status: Planned  
Priority: P0  
Owner: Frontend + Product + Localization  
Date: 2026-05-29

## Priority Order

This task is the first P0 delivery item in current UX improvement cycle.

## Problem

RU interface contains incorrect terms and mixed-language strings.
This lowers clarity and product trust.

## Goal

Normalize terminology and eliminate broken/mixed translations in production UI.

## Scope

1. collect all i18n keys used in frontend,
2. find fallback values and unresolved keys,
3. find machine-like/incorrect translations,
4. find English strings in RU UI,
5. find Polish strings in RU UI,
6. create canonical HostFlow terminology glossary for RU locale.

## Out of Scope

- redesign of screen structure,
- language expansion strategy,
- content rewrite outside current UI copy.

## Acceptance Criteria

1. No visible mixed-language strings in RU UI for audited modules.
2. Known bad labels are fixed (examples: incorrect literal translations).
3. Every corrected term has canonical mapping in glossary.
4. Fallback behavior is explicit and consistent.
5. Regression list for translations is added to QA checklist.

## Dependencies

- i18n resource files,
- localization ownership and approval flow.

## Input Audit Required Before Build

- `docs/specs/tasks/p0_translation_audit.md`
