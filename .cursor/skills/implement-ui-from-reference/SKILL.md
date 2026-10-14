---
name: implement-ui-from-reference
description: Implements a UI change from a mock, screenshot, or reference screen by reusing HostFlow primitives and checking ADR-011. Use when building or restyling a page, including an employee or entity page.
---

# Implement UI from reference

1. Read the reference.
2. Identify the existing system primitives that already cover it.
3. Map each reference element to one of those primitives.
4. Implement that mapping.
5. Verify the screen visually.
6. Run `node scripts/check-adr011-ui-patterns.mjs --fail` from `hostflow-frontend`. Fix only violations introduced by this change, and report the result.
7. Read the diff against the mapping.

Do not introduce a local task, note, document, status, dictionary, form-control, or styling system.
