# Stage 1B — Quote Money & Tax Arithmetic

**Status:** design-first (normative for PR-1)  
**Parent:** [`stage-1b-quote-object-model.md`](stage-1b-quote-object-model.md)

All Quote totals and future Invoice handoff **must** use this spec. No float/double anywhere.

---

## 1. Types & scale

| Field | SQL type | API wire | Scale | Min | Max |
|-------|----------|----------|-------|-----|-----|
| `unit_price`, `line_total`, `tax_amount`, subtotals | `NUMERIC(18,4)` | decimal string | 4 dp | `0.0000` | `999999999999.9999` |
| `quantity` | `NUMERIC(18,6)` | decimal string | 6 dp | `0.000001` | `999999999999.999999` |
| `tax_rate` | `NUMERIC(8,6)` | decimal string | 6 dp | `0.000000` | `1.000000` |

---

## 2. Price basis

**`unit_price` is tax-exclusive** (net). This matches B2B Invoice expectation in ADR-004 handoff.

`tax_rate = null` or absent on a line → treat as **`0`** (zero-rated / out of scope). Do not inherit quote-level default in PR-1.

---

## 3. Rounding

- **Mode:** `ROUND_HALF_UP` (away from zero) to field scale.
- **Per-line first:** compute each line, round line amounts, then sum.
- **Do not** compute tax on unrounded aggregate subtotal.

---

## 4. Formulas (per line `i`)

```text
line_total_i  = ROUND_HALF_UP(quantity_i × unit_price_i, 4)
tax_amount_i  = ROUND_HALF_UP(line_total_i × effective_tax_rate_i, 4)
effective_tax_rate_i = tax_rate_i ?? 0
```

## 5. Formulas (version totals)

```text
subtotal  = Σ line_total_i
tax_total = Σ tax_amount_i
total     = ROUND_HALF_UP(subtotal + tax_total, 4)
```

Store `subtotal`, `tax_total`, `total` on `quote_versions` after every draft PATCH and at send freeze.

---

## 6. Currency rule

- `quotes.currency` is **required** on create.
- `scope_snapshot.currency` **must equal** `quotes.currency` (case-sensitive ISO 4217) on every write and at send.
- Each `items[]` line inherits quote currency implicitly; per-line currency field is **forbidden** in schema v1.

Mismatch → `422 currency_mismatch`.

---

## 7. Validation failures

| Code | When |
|------|------|
| `422` | quantity/price out of range, scale overflow, currency mismatch |
| `422` | empty `items[]` at send |

---

## 8. Test vectors (implementation PR)

| Case | quantity | unit_price | tax_rate | line_total | tax_amount |
|------|----------|------------|----------|------------|------------|
| Simple | 1 | 1500 | 0.23 | 1500.0000 | 345.0000 |
| Fractional qty | 1.5 | 100 | 0.23 | 150.0000 | 34.5000 |
| Zero tax | 2 | 50 | null | 100.0000 | 0.0000 |
| Half-up edge | 3 | 10.3333 | 0.23 | 30.9999 | 7.1300 |
