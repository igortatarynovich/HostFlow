# Acquisition UI Cutover C-6 — Form Builder cutover

**Status:** READY TO IMPLEMENT — **ACTIVE Product Track** (after C-5 Mapping workspace)  
**Date:** 2026-07-26  
**Canon:** [acquisition-ui-cutover.md](acquisition-ui-cutover.md) (C-6 row + Forms zone)  
**Parents:** ADR-024 · ADR-007 (Forms SoT) · [C-5 Mapping](acquisition-ui-cutover-c5-mapping-workspace.md) · [sales-to-comms-sequential-queue.md](sales-to-comms-sequential-queue.md)  
**Next:** C-7 Подборы decommission + cutover PASS  
**Blocks:** Stage 5 PR-2 remains paused until cutover C-7 PASS

> C-6 closes **Forms inside Marketing IA**: list / edit / activate / public URL from Marketing, plus **create-new-form in Connect Source / Setup** — without leaving the Campaign onboarding path.  
> **Not** a second Forms runtime. **Not** Forms platform Composition publish rebuild. **Not** C-7 Подборы retirement.

---

## 1. Why now

C-3…C-5 deliver Source inventory, sample discovery, and mapping. Operators still create/edit HostFlow forms only under **Settings → Lead forms**, and Connect Source **select-existing** only (empty state links out to Settings). That breaks the locked onboarding path:

```text
Connect → Source → Test Lead → Mapping → [C-6 Forms in Marketing] → Destination → Flight → First Lead
```

---

## 2. Product job (one sentence)

A non-developer operator can **create, edit, activate, and copy a public URL** for a HostFlow form from **Marketing**, and from Campaign Connect Source choose **select-existing or create-new** without treating Settings as the only Forms path.

---

## 3. Locked boundary

| Concern | Today (Settings) | C-6 | OUT |
|---------|------------------|-----|-----|
| Forms SoT (`TenantLeadForm` / ADR-007) | ✅ | ✅ same SoT | ❌ second registry / Marketing-only copy |
| List / create / edit / activate / slug | Settings routes | Marketing routes + Settings redirect/deeplink | ❌ delete Settings Forms before redirects live |
| Composition Builder draft (`/platform/forms/builder`) | Settings `…/builder` | Same builder under Marketing path | ❌ invent new publish HTTP for Composition in this slice |
| Operator “publish” | `is_active` + `public_slug` | same verbs | ❌ claim `commit_publish` SPA unless already exposed |
| Connect Source HostFlow form | select-existing only | select **and** create-new-in-flow | ❌ Meta Graph form builder |
| Mapping / Sources / Diagnostics | C-3…C-5 / post–C-7 | deep-links only | ❌ absorb Mapping or Diagnostics |

**Rule:** C-6 is **navigation + workflow remount**. Reuse existing pages/APIs. Do **not** fork Forms platform.

---

## 4. Donor / reuse (do not re-invent)

| Need | Donor |
|------|--------|
| List + create | `LeadFormsSettingsPage` + `createIntakeForm` → `POST /api/v1/settings/intake-forms` (**not** bare `POST /settings/lead-forms`) |
| Detail / activate / slug / presentation | `IntakeFormDetailPage` |
| Composition draft editor | `FormsBuilderPage` + `/api/v1/platform/forms/builder/*` |
| Select existing in Setup | `MarketingConnectSourcePage` + `listLeadForms` + `attachCampaignForm` |
| Paths / codegen | `shared/crm_app_paths.json` → add `marketingForms`; keep `settingsLeadForms` as alias/redirect |
| Nav rail | `SIDEBAR_AGENCY_MARKETING_ORDER` — add Forms item |

**Forbidden:** new Forms tables; Marketing-only form DTO; Graph live-fetch as Forms SoT; Подборы launch UI changes (C-7).

---

## 5. UX sketch (minimum)

1. Marketing sidebar → **Forms** → `/app/marketing/forms` (same inventory UX as Settings list).  
2. Detail + builder under `/app/marketing/forms/:formId` and `…/builder` (reuse components; back-links to Marketing).  
3. Settings `/app/settings/lead-forms…` → redirect (or soft deeplink) to Marketing equivalents so bookmarks survive.  
4. Connect Source (`public_form`): **Create form** CTA → `createIntakeForm` (inline modal/wizard or short page) → auto-select new form → optional attach to Campaign/Flight.  
5. Empty-state no longer dead-ends at Settings-only.

---

## 6. Publish verb (locked for this slice)

| Verb in UI | Meaning |
|------------|---------|
| **Active** | `TenantLeadForm.is_active = true` (available in pickers) |
| **Public URL** | `public_slug` set; status label may show `published` when active+slug (existing `form_publication_status`) |
| **Composition draft** | Builder draft GET/PUT — **not** claimed as operator publish |

Do not rename these into a new Marketing-only lifecycle in C-6.

---

## 7. OUT

- Подборы decommission (C-7)  
- Source Diagnostics epic  
- Stage 5 PR-2  
- New mapping engine / C-5 expansion  
- Meta Lead Form creation inside HostFlow  
- Billing pack redesign (quota still enforced on create/activate)  
- Removing Settings Integrations (Meta OAuth stays Settings)

---

## 8. Acceptance

- [ ] Marketing rail includes Forms; `/app/marketing/forms` lists forms  
- [ ] Operator can create/edit/activate/copy public URL from Marketing paths  
- [ ] Builder reachable under Marketing path (same donor)  
- [ ] Settings lead-forms URLs redirect or deeplink to Marketing equivalents  
- [ ] Connect Source supports select-existing **and** create-new-in-flow (uses `createIntakeForm`)  
- [ ] No second Forms SoT; no Composition `commit_publish` invention unless already productized  
- [ ] Cutover docs: C-6 DONE; Product Track → C-7  
- [ ] Tests: route/nav scope scans + Connect Source create path; `make docs-lint`  

---

## 9. Implementation order (PR split)

1. **Docs / brief** (this file) + queue linkage  
2. **IA:** `marketingForms` paths + routes remounting Settings donors + Marketing nav + Settings redirects  
3. **Create-in-setup:** Connect Source create-new using `createIntakeForm`  
4. Close-out docs + smoke  

---

## 10. STOP conditions

- Any PR that adds a parallel form store or Marketing-only mapping registry  
- Claiming Composition Builder HTTP publish without an existing operator route  
- Deleting Settings Forms entry before Marketing path + redirects ship  
- Touching Подборы launch / C-7 scope in the same PR  
