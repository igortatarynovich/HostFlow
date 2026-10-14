---
name: canonical-migration
description: Migrates authority or implementation from a source onto its canonical target. Use when moving behavior such as Candidate to System to Employee, cutting over named consumers, or promoting source behavior into an existing primitive.
---

# Canonical migration

identify source → identify canonical target → preserve explicitly requested migration direction → promote source behavior into canonical target → migrate named consumers → verify source behavior remains unchanged → run checks for affected surfaces → stop on canonical gap.

When the task also changes models or schema, follow `.cursor/rules/database.mdc` for Alembic and seeds. Those steps are not part of this procedure.
