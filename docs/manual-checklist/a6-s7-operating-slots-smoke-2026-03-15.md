# A6-S7 Operating Slots Smoke Report

- Generated at (UTC): `2026-03-15T11:29:47.019615+00:00`
- Overall status: `PASS`
- Synthetic tenant slug: `a6-s7-smoke-054e6276`

## Steps

| Step | Status | Detail |
|---|---|---|
| `initial-slots` | `PASS` | effective=1, used=0 |
| `create-first-operating` | `PASS` | used=1 and available=0 |
| `block-second-before-addon` | `PASS` | second operating create blocked before add-on slot |
| `add-slot` | `PASS` | effective=2, available=1 |
| `create-second-after-addon` | `PASS` | used=2 |
| `downgrade-over-limit-state` | `PASS` | effective=1, used=2 |
| `block-new-after-downgrade` | `PASS` | new operating create blocked after downgrade |
| `data-preserved-after-downgrade` | `PASS` | operating companies persisted=2 |

## Slot Snapshots

| Snapshot | included | extra | effective | used | available | unlimited |
|---|---:|---:|---:|---:|---:|---|
| `initial` | 1 | 0 | 1 | 0 | 1 | NO |
| `after_first_create` | 1 | 0 | 1 | 1 | 0 | NO |
| `after_addon` | 1 | 1 | 2 | 1 | 1 | NO |
| `after_second_create` | 1 | 1 | 2 | 2 | 0 | NO |
| `after_downgrade` | 1 | 0 | 1 | 2 | 0 | NO |
