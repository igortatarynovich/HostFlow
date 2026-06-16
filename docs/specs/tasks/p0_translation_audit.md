# P0 Audit: Translation Audit (RU UI)

Status: Required pre-implementation  
Date: 2026-05-29  
Owner: Product + Frontend + Localization

## Purpose

Create factual correction list before translation cleanup implementation.

## Collect

1. i18n key,
2. current RU value,
3. correct RU value,
4. issue type:
- wrong translation,
- mixed language,
- fallback leak,
- typo/grammar.
5. module/screen location.

## Minimum Output Table

| Key | Current Value | Correct Value | Issue Type | Module/Screen |
|---|---|---|---|---|
|  |  |  |  |  |

## Required Checks

1. English text visible in RU locale.
2. Polish text visible in RU locale.
3. Missing key fallback values.
4. Inconsistent terminology for same concept.

## Decision Use

Results become direct input for:

- `p0_ui_translation_cleanup.md`

No cleanup implementation starts until this audit table is populated.
