# Self-service Success Path & Setup Wizard

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

## 2. Success Path (canonical)

```text
Landing (/)
  → Signup (/signup)
  → Setup Wizard (/app/platform/setup → guided steps)
  → Connect Meta (or deferred with checklist debt)
  → Create order (when Sales path applies) / Create vacancy
  → Publish / open intake
  → Receive lead
  → Contact
  → Convert to candidate
  → Close vacancy
  → Invoice (plan-gated; Business+)
```

Candidate funnel is **out of band** (tokenized `/public/*`) — ADR-034.

---

## 3. Setup Wizard (target UX)

Post-account HostFlow must **not** drop the user into an empty CRM. Wizard steps:

| Step | Intent | Existing runtime (today) | Target |
|------|--------|--------------------------|--------|
| 1 | Company name | Platform setup details | Keep |
| 2 | Country | Platform setup | Keep |
| 3 | What the company does | Identity + industry | Keep / clarify copy |
| 4 | Modules needed | First-module intent | Map to Launchpad enablement |
| 5 | Connect Meta | Setup hub / integrations | In-wizard or hard next CTA |
| 6 | Invite colleagues | Team settings | In-wizard or checklist |
| 7 | First order | Setup / Sales | Guided when Sales on |
| 8 | First vacancy | `/app/setup/vacancy` | Required for recruitment path |

**Time box:** ≤ 10 minutes to “workspace ready”. Skip allowed with checklist debt (visible until cleared).

### Onboarding checklist (in-app)

- [ ] Company created  
- [ ] Teammates invited (optional)  
- [ ] Meta connected (or deferred)  
- [ ] First vacancy created  
- [ ] First lead received  
- [ ] First contact with candidate  

### Empty states

Every empty list must state **what to do next** + primary CTA (not “nothing here”).

---

## 4. Growth surface backlog (priority)

Per ADR-034 and product priority:

| Phase | Surface | Outcome |
|-------|---------|---------|
| **0** | Canon (this doc + ADR-034) | One IA; no parallel landings |
| **1** | Landing reposition + how-it-works (≤5) + pricing honesty | Understand value in 10–15s |
| **2** | Setup Wizard + checklist + empty-state CTAs | First value without support |
| **3** | FAQ hub (`/faq`, ~80–100 Q by section) | SEO + deflection |
| **4** | SEO factory (industry / role / integration pages) | Organic growth |
| **5** | User docs + Academy + product tours + context help | Depth after path works |
| **Demo** | Interactive demo tenant | After Phase 2 security/reset policy |

---

## 5. How-it-works (marketing, ≤5 steps)

1. Create company  
2. Connect Meta  
3. Create vacancy  
4. Receive applications  
5. Process candidates  

---

## 6. Pricing honesty (Growth)

Landing pricing must disclose, aligned to [`plans-matrix.md`](../plans-matrix.md):

- what is included / excluded per plan;
- seats, workspaces, lead and vacancy limits;
- what happens when Trial ends (caps map to plan; paid checkout).

Do not invent limits not present in plans-matrix / billing code.

---

## 7. Acceptance (Phase 1–2)

**Phase 1 (landing):** first viewport answers the four ADR-034 questions; how-it-works has five steps; pricing shows trial/limits clarity; all Growth CTAs → `/signup`.

**Phase 2 (wizard):** new tenant completes company + vacancy (and sees Meta/invite checklist) without opening a support ticket; empty vacancies state CTAs to create vacancy.

---

## 8. Non-goals (this journey)

- Replacing operator Acquisition CRM (`/app/marketing`).
- Merging candidate intake into Growth homepage.
- Shipping Academy/video before Phase 2 path is green.
