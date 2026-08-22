# CHECKBOX_V1

Status: **Locked**  
Draft date: 2026-08-21  
Locked date: 2026-08-21  
Governance: Approved (Workspace Capability Platform — boolean proof blocker)  
Input: `PRIMITIVES_V1.md`, Field Registry `boolean`, `FOUNDATION_V1.md`  
Authority: `REF-UI-*` + [Workspace Capability Platform Completion](../tasks/workspace-capability-platform-completion.md)

## Question Answered

> Какой один checkbox-control разрешён для canonical `boolean` fields — без локального `<input type="checkbox">`?

`boolean` is a Field Registry type. Consent (and any boolean `field_row`) must use this primitive. Local `<input type="checkbox">` is **forbidden in new code**. Legacy pages migrate on touch.

This family was deferred when Layer 2 closed. It is reopened **only** for checkbox. Radio and Toggle stay deferred.

---

## Governance

| Rule | Detail |
|---|---|
| Authority | `REF-UI-*` |
| New code | Must use `<Checkbox>` from `components/ui/Checkbox.tsx` |
| Visual source | `.checkbox-field` / `.checkbox` / `.checkbox-label` in `components.css` |
| Max variants | **1** control — no switch/toggle alias |
| Local native checkbox | **Forbidden** in new code (including G4 consent) |
| Changes | Explicit governance decision in `REF-UI-*` |

---

## 1) Component contract

**Path:** `hostflow-frontend/src/components/ui/Checkbox.tsx`

```tsx
type CheckboxProps = {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: ReactNode
  description?: ReactNode
  disabled?: boolean
  name?: string
  id?: string
  className?: string
}
```

| Rule | Detail |
|---|---|
| Element | Native `<input type="checkbox">` **inside** the primitive only |
| Label | Clicking the label toggles |
| Disabled | No toggle; `aria-disabled` via native `disabled` |
| CRM | Lives under `.app-ui`; do not invent a second size scale |

---

## 2) When to use

| Use Checkbox | Do not use Checkbox |
|---|---|
| Field Registry `boolean` | Multi-select lists (`reference_code[]` → Select) |
| Consent / policy acknowledgement | Status display (`StatusBadge`) |
| Single on/off confirmation | Filter chips (`Chip` selectable) |

---

## 3) Migration

Migrate on touch. Do not bulk-replace existing pages in this lock. G4 Consent widget **must** use this primitive on first bind.

---

## 4) Related

- Data type: `boolean` in Field Registry §4  
- Kit: `KIT_UI_PRIMITIVE_IDS` includes `checkbox`  
- Proof: Recruitment Application consent must not ship `<input type="checkbox">` outside this component  
