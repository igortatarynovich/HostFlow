# Workspace Capability — legacy local forks inventory

**Status:** **INVENTORY** (feat; not a migration)  
**Parents:** [Workspace Capability Platform Completion](workspace-capability-platform-completion.md)  
**Canon replacement for local widgets:** shared `notes` / `consent` and module contributions via the Capability Host Contract

> Inventory ≠ migrate every row. Proof screen (next slice) must not add a **new** row.
> Forms consent-at-capture (ADR-007) is **not** a Notes/Consent fork to absorb here.

---

## Hosts in scope

| Host | Constitution | Runtime today |
|------|--------------|---------------|
| `entity_workspace` | §3.3 | `EntityWorkspaceShell` |
| `application_workspace` | §3.2 | `ApplicationWorkspace` |

---

## Local widgets that violate the restored goal

| Local widget | Consumer | Host | Maps toward | Evidence |
|--------------|----------|------|-------------|----------|
| `SalesInquiryCallNotesSection` | Sales Inquiry | Application | shared `notes` | `components/sales/SalesInquiryCallNotesSection.tsx`; composed in `ApplicationSalesDetailPanel` |
| `SalesInquiryRodoSection` | Sales Inquiry | Application | shared `consent` + policy `lead_rodo_v1` | `components/sales/SalesInquiryRodoSection.tsx` |
| `CandidateRodoSection` | Candidate | Entity | shared `consent` (transport ≠ capability) | `components/candidate/CandidateRodoSection.tsx`; `CandidateCard` / `CandidateCommunicationSection` |
| Recruitment Application ContextRail `vacancy` | Recruitment Application | Application | `recruitment.vacancy` | `ApplicationRecruitmentDetailPanel` `contextSlots.vacancy` |
| Recruitment Application ContextRail `assignee` | Recruitment Application | Application | `recruitment.assignee` | `ApplicationRecruitmentDetailPanel` `contextSlots.assignee` |
| Recruitment Application stage / decision JSX | Recruitment Application | Application | `recruitment.stage` | `resolveRecruitmentApplicationDecision` + `ContextRail` `decision` |
| Recruitment Application contacts chrome | Recruitment Application | Application | shared `contacts` / shell identity | `contextSlots.contacts` |
| Recruitment comments / RODO (missing shared bind) | Recruitment Application | Application | shared `notes` / `consent` | No contribution bind; parent still free to stuff local sections |

Sales CallNotes/RODO remain inventory until migrate-on-touch. They are **not** the G4 proof.

---

## Proof screen must not add a row

G4 (next slice) binds Recruitment Application through contributions. If `ApplicationRecruitmentDetailPanel` still decides “RODO here, comments there, stage below” in parent JSX, G4 fails.

This feat does **not** rewrite that panel.
