# Self-service Success Path (guided readiness UI)

**Status:** L2 operating canon (journey + activation)  
**Owner:** product + frontend  
**Architecture:** [ADR-034](../architecture/ADR-034-self-service-public-funnels.md)  
**Plans SoT:** [`plans-matrix.md`](../plans-matrix.md)

---

## 1. Goal

Any new buyer reaches **first operational value without support**:

company ready → Meta (or skip with clear reason) → first order/vacancy → inbound lead path understood → contact candidate.

If this path works end-to-end, HostFlow is ready to scale acquisition.

---

## 2. Product decision: clear UI, not wizard magic

**Canonical activation UX is a guided readiness interface inside the normal product shell** — not an 8-step Setup Wizard that traps the user in a separate onboarding mode.

| Do | Do not |
|----|--------|
| Always show **where I am** and **what to do next** | Force a linear 1→8 wizard for Meta / invite / vacancy / order |
| Short **company identity form** only where data is mandatory | Re-ask identity in a multi-screen “tour” after company exists |
| Persistent **checklist + next CTA** on home / setup hub | Hide progress until the wizard finishes |
| **Empty states** with one primary action | “Nothing here yet” with no path forward |
| Allow skip with visible checklist debt | Block the app until every optional step is done |
| Full CRM for a standalone employer (`type=company` without inbound `TenantLink`) | Treat self-serve signup as Citronex-style client-view (masked candidates, truncated menu) |

**Allowed narrow form:** `/app/platform/setup` (or equivalent) collects company name / country / activity once — then the user lands in the real CRM with a readiness panel, not another wizard.

**Not user-facing:** Recruitment technical gates G0–G8 (`SetupStatusPanel` / setup-readiness API) stay as **operator/health internals**. They must not appear on the buyer Success Path screens.

---

## 3. Success Path (canonical)

```text
Landing (/)
  → Signup (/signup)
  → Company identity (short form — mandatory once)
  → Product home / setup hub with readiness checklist + next action
  → Connect Meta (CTA; deferrable)
  → Create order (when Sales path applies) / Create vacancy (CTA from empty state)
  → Publish / open intake
  → Receive lead
  → Contact
  → Convert to candidate
  → Close vacancy
  → Invoice (plan-gated; Business+)
```

Candidate funnel is **out of band** (tokenized `/public/*`) — ADR-034.

---

## 4. Readiness UI (target)

Post-account HostFlow must **not** drop the user into an empty CRM with no next step. After company identity:

### Readiness checklist (in-app, persistent until cleared)

- [ ] Company created  
- [ ] Teammates invited (optional)  
- [ ] Meta connected (or deferred)  
- [ ] First vacancy created  
- [ ] First lead received  
- [ ] First contact with candidate  

### Next-action rule

Exactly **one primary CTA** on the readiness surface (“Create vacancy”, “Connect Meta”, …). Secondary links allowed; no competing heroes.

### Empty states

Every empty list must state **what to do next** + primary CTA (not “nothing here”).

Canonical empty CTAs for the Success Path:

| Screen | Empty message focus | Primary CTA |
|--------|---------------------|-------------|
| Vacancies | Create first vacancy (~30s) | Create vacancy |
| Leads | Applications will land here | Create vacancy → then Connect ads |
| Candidates | Appear after qualifying a lead | Open leads |
| Pipeline | Process a lead into a candidate | Open leads |
| Follow-ups / tasks | Appear after first contact | Open leads |

### Existing runtime (map, do not invent parallel IA)

| Intent | Today | Target |
|--------|-------|--------|
| Company identity | `/app/platform/setup` | Keep as short form only |
| Module / first path | Launchpad | Clarify next step copy |
| Recruitment setup | `/app/setup` hub | Become readiness home + checklist |
| Meta | Integrations / setup | Checklist item + deep link CTA |
| First vacancy | Setup vacancy / empty vacancies | Empty-state CTA |
| Invite | Team settings | Checklist item + deep link |

**Time box:** ≤ 10 minutes to “workspace ready” (company + first vacancy path visible). Optional steps may remain open as checklist debt.

---

## 5. Growth surface backlog (priority)

Per ADR-034 and product priority:

| Phase | Surface | Outcome |
|-------|---------|---------|
| **0** | Canon (this doc + ADR-034) | One IA; no parallel landings |
| **1** | Landing reposition + how-it-works (≤5) + pricing honesty | Understand value in 10–15s |
| **2** | Readiness UI + checklist + empty-state CTAs | First value without support |
| **3** | FAQ hub (`/faq`) + light context help on key terms | SEO + deflection without leaving the screen |
| **4** | SEO factory (industry / role / integration pages) | Organic growth — **Wave-2 shipped** via `seoPageCatalog` + `SeoCatalogPage` (8 pages); Wave-1 hand-built pages remain |
| **5** | User docs + Academy | Depth after path works — **Wave-1 shipped**: `/docs`, `/docs/:slug` (8 how-tos), `/academy` (lessons → docs; video slots ready) |
| **Demo** | Interactive demo | **Wave-1 shipped**: public `/demo` + per-tenant sample pack (seed/clear). Shared anonymous guest tenant = deferred (see security threat model) |

Phase 5 **product tours** (if any) are short contextual tips — not a replacement for readiness UI and not a forced wizard. Context help already links FAQ + Docs.

**Phase 4 (Wave-2) routes:** `/use-cases/recruitment-agencies`, `/use-cases/transport-companies`, `/use-cases/driver-recruitment`, `/features/whatsapp-recruitment`, `/features/meta-ads-recruitment`, `/use-cases/ats-for-drivers`, `/use-cases/ats-for-transport`, `/use-cases/ats-europe`. Catalog SoT: `hostflow-frontend/src/content/seo/seoPageCatalog.ts`.

**Phase 5 (Wave-1) routes:** `/docs`, `/docs/getting-started`, `/docs/create-company`, `/docs/connect-meta`, `/docs/first-vacancy`, `/docs/first-lead`, `/docs/first-candidate`, `/docs/documents-basics`, `/docs/invite-team`, `/academy`. Catalog SoT: `hostflow-frontend/src/content/docs/`.

**Demo (Wave-1):** `/demo` (Growth). In-app: readiness panel «Load sample data» / «Clear sample data» → `POST /onboarding/demo/seed` / `POST /onboarding/clear-demo-data`. Policy: [`interactive-demo.md`](../../security/threat-models/interactive-demo.md).

### Demo policy (normative)

| Do | Do not (Wave-1) |
|----|-----------------|
| Own workspace via `/signup`, then seed sample pack | Shared guest login everyone mutates |
| Clear sample pack in one action | Leave demo rows indistinguishable from real CRM data |
| Market `/demo` as the explanation + CTA into signup | Expose live tenant data to anonymous visitors |

---

## 6. How-it-works (marketing, ≤5 steps)

1. Create company  
2. Connect Meta  
3. Create vacancy  
4. Receive applications  
5. Process candidates  

---

## 7. Pricing honesty (Growth)

Landing pricing must disclose, aligned to [`plans-matrix.md`](../plans-matrix.md):

- what is included / excluded per plan;
- seats, workspaces, lead and vacancy limits;
- what happens when Trial ends (caps map to plan; paid checkout).

Do not invent limits not present in plans-matrix / billing code.

---

## 8. Acceptance (Phase 1–5)

**Phase 1 (landing):** first viewport answers the four ADR-034 questions; how-it-works has five steps; pricing shows trial/limits clarity; all Growth CTAs → `/signup`.

**Phase 2 (readiness UI):** new tenant completes company identity, then sees a clear next action toward vacancy/Meta without a multi-step wizard; empty vacancies state CTAs to create vacancy; checklist debt remains visible if Meta/invite skipped.

**Phase 3 (FAQ):** `/faq` hub + `ContextHelp` on key product screens; CTAs stay on Growth funnel (`/signup`).

**Phase 4 (SEO factory Wave-2):** catalog-driven pages render from `SEO_PAGE_CATALOG`; unique Title/H1/FAQ; primary CTA → `/signup`; listed in `sitemap.xml` and page registry.

**Phase 5 (Docs + Academy Wave-1):** `/docs` hub + Success Path how-tos; `/academy` lesson index linking to docs (video optional); ContextHelp links to docs + FAQ; primary CTAs still → `/signup`.

**Demo (Wave-1):** `/demo` explains interactive try path; sample pack seed/clear inside the buyer’s own tenant; no shared anonymous guest tenant ([`interactive-demo.md`](../../security/threat-models/interactive-demo.md)).

---

## 9. Non-goals (this journey)

- Replacing operator Acquisition CRM (`/app/marketing`).
- Merging candidate intake into Growth homepage.
- Shipping Academy/video before Phase 2 path is green.
- Building an 8-step Setup Wizard as the primary activation product.
