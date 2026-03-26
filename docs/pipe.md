HOSTFLOW PRODUCT BLUEPRINT  
(Complete consolidated analysis based on the Pipedrive product study and UX/CRM patterns)

---------------------------------------------------------------------

1. PURPOSE OF THIS DOCUMENT

This document consolidates the full analysis of Pipedrive and translates the findings into a product architecture for HostFlow.

Goal:

Take the strongest ideas from Pipedrive and apply them to a specialized ATS/CRM for transport recruitment.

This document includes:

- product philosophy
- UX patterns
- interface architecture
- automation logic
- pipeline design
- table structure
- dashboards
- compliance features
- candidate workflow
- performance principles

---------------------------------------------------------------------

2. WHY USERS CHOOSE PIPEDRIVE

The main reason users choose Pipedrive is not the number of features.

It is because the product removes friction from daily CRM work.

Users consistently highlight:

- ease of use
- intuitive UI
- visual pipeline
- quick onboarding
- clarity of workflow
- simple automation
- operational visibility

Pipedrive does not try to be the most powerful CRM.

Instead it focuses on being the most usable operational tool.

Key idea:

CRM should guide the user through work.

Not just store data.

This is the core principle HostFlow should adopt.

---------------------------------------------------------------------

3. CORE PRODUCT PHILOSOPHY

Pipedrive is a process-first CRM.

The product is built around movement of entities through stages.

Pipedrive entity flow:

Lead → Deal → Pipeline → Activities → Reporting

HostFlow equivalent:

Lead source → Candidate → Vacancy → Documents → Permit/Visa → Arrival → Employment

The system must represent the real workflow of the business.

The interface must show:

- where entities are
- what stage they are in
- what the next step is
- where problems exist

---------------------------------------------------------------------

4. PRIMARY UX PRINCIPLES

Principle 1 — One screen = one purpose

Each screen must answer one clear question.

Pipeline screen → where candidates are  
Table screen → operational work  
Dashboard → performance overview  
Profile screen → candidate details  

Avoid mixing too many functions on one screen.

---------------------------------------------------------------------

Principle 2 — Visible next action

Every entity should display:

"What should I do next?"

Example:

Next action: Call candidate

Entities without next action are operational risks.

HostFlow rule:

Candidate without next action = problem.

---------------------------------------------------------------------

Principle 3 — Minimal clicks

Important actions should require:

≤ 3 clicks

Examples:

Add candidate  
Upload document  
Assign manager  
Create task  

---------------------------------------------------------------------

Principle 4 — Action-driven CRM

CRM should behave like a task engine.

Instead of static records.

Pipedrive enforces activities.

HostFlow should enforce next steps.

---------------------------------------------------------------------

Principle 5 — Fast interface

Speed directly affects adoption.

Target performance:

Page load < 200 ms  
Table filter < 100 ms  
Search instant  

Slow CRM systems are abandoned by teams.

---------------------------------------------------------------------

5. GLOBAL INTERFACE ARCHITECTURE

Modern CRM systems use a three-layer layout.

Top bar  
Sidebar  
Workspace

Layout:

Top bar  
Sidebar navigation  
Main workspace

Top bar contains:

- global search
- quick actions
- notifications
- user menu

Sidebar contains system modules.

Workspace contains operational screens.

---------------------------------------------------------------------

6. SIDEBAR STRUCTURE

Sidebar modules for HostFlow:

Dashboard  
Candidates  
Vacancies  
Companies  
Documents  
Activities  
Reports  
Settings  

Sidebar properties:

- fixed position
- darker color
- visually separated from content

Purpose:

Users always know where they are in the system.

---------------------------------------------------------------------

7. COLOR SYSTEM

A disciplined color system reduces cognitive load.

Base background

Very light.

Examples:

#FFFFFF  
#F7F8FA  

Navigation background

Dark.

Example:

#1F2937  

Primary action color

One main color for actions.

Used for:

buttons  
progress  
confirmations  

Status colors

Success → Green  
Warning → Amber  
Danger → Red  
Info → Blue  
Neutral → Grey  

HostFlow statuses:

Ready → Green  
Missing docs → Amber  
Blocked → Red  
Processing → Blue  

---------------------------------------------------------------------

8. TYPOGRAPHY

Use one font family.

Examples:

Inter  
Roboto  
System UI  

Size hierarchy:

Page title → 24 px  
Section title → 18 px  
Card title → 16 px  
Body text → 14 px  
Meta text → 12 px  

This allows fast scanning.

---------------------------------------------------------------------

9. SPACING SYSTEM

Use an 8 px grid.

Spacing values:

8  
16  
24  
32  
48  
64  

Example card padding:

16 px on all sides

Spacing between sections:

24 px

Spacing between cards:

16 px

---------------------------------------------------------------------

10. BUTTON SYSTEM

Primary button

Main action.

Example:

Add candidate

Secondary button

Less important actions.

Examples:

Edit  
Export  

Ghost button

Low priority actions.

Example:

View details

Danger button

Example:

Delete

---------------------------------------------------------------------

11. DATA MODEL STRUCTURE

Pipedrive entities:

Leads  
Deals  
People  
Organizations  
Activities  
Products  
Emails  

HostFlow entities:

Lead source  
Candidate  
Vacancy  
Company  
Documents  
Activities  
Compliance events  

Key principle:

Candidate card is the source of truth.

All changes originate from the candidate record.

---------------------------------------------------------------------

12. AUTOMATION SYSTEM

Automation should be event driven.

Important triggers:

Candidate created  
Stage changed  
Document uploaded  
Document expiring  
Candidate linked to vacancy  
Candidate stuck in stage  

---------------------------------------------------------------------

Candidate created

Automation:

Assign recruiter  
Create initial tasks

Example tasks:

Call candidate  
Send document list  
Verify driver license  
Verify Code95  

---------------------------------------------------------------------

Candidate linked to vacancy

Automation:

Load vacancy requirements  
Create document checklist  
Generate onboarding tasks

Example required documents:

Driver license  
Code 95  
Tachograph card  
Passport  
Residence permit  

---------------------------------------------------------------------

Document uploaded

Automation:

Check expiration date.

If expiration < 60 days

Trigger warning badge.

---------------------------------------------------------------------

Stage changed

System verifies:

Required documents  
Compliance conditions  

If requirements missing:

Stage change blocked or warning displayed.

---------------------------------------------------------------------

Stage templates

Each stage generates tasks.

Example:

Stage: Work permit ordered

Tasks:

Submit application  
Upload confirmation  
Check processing status  

---------------------------------------------------------------------

Candidate stuck detection

Example:

Candidate in stage:

Contact established

> 7 days

System displays:

Stuck candidate warning.

---------------------------------------------------------------------

Smart reminders

Example:

Permit ordered  
Expected processing: 30 days  

Reminder at day 25:

Check permit status.

---------------------------------------------------------------------

13. PIPELINE VISUALIZATION

Pipeline summary shows counts.

Example:

New 24  
Contacted 18  
Waiting documents 11  
Permit ordered 6  
Planning arrival 4  
On base 3  
Driving 8  
Hired 14  
Rejected 5  

Stage card example:

Waiting documents  
11 candidates  
Average time 6 days  

Clicking a stage filters the table.

---------------------------------------------------------------------

14. CANDIDATES SCREEN ARCHITECTURE

The candidates screen is the main operational screen.

Structure:

Header  
Pipeline summary  
Filters  
Candidates table  

Header

Candidates  
Add candidate

Search candidates

Export

---------------------------------------------------------------------

Filters

Saved views:

All candidates  
My candidates  
Missing documents  
Ready drivers  
Arrival this week  

Filter fields:

Stage  
Manager  
Company  
Vacancy  
Documents status  
Citizenship  
Created date  

---------------------------------------------------------------------

Candidates table columns

Candidate  
Stage  
Manager  
Company  
Vacancy  
Documents  
Readiness score  
Last contact  
Next action  
Created date  

---------------------------------------------------------------------

Candidate column example

Ivan Petrov  
+380675555  
Ukraine  

---------------------------------------------------------------------

Documents column

Example:

3 / 5

Hover reveals:

Passport  
Driver license  
Code95  
Tachograph card  
Residence permit  

---------------------------------------------------------------------

Readiness score

Example:

82 %

Based on:

Documents completeness  
Compliance  
Stage progress  

---------------------------------------------------------------------

Next action column

Example:

Call candidate  
Today  

---------------------------------------------------------------------

Bulk actions

Assign manager  
Change stage  
Send message  
Export  
Delete  

---------------------------------------------------------------------

15. CANDIDATE QUICK PREVIEW

Side panel preview allows fast access.

Example:

Candidate name  
Stage  
Manager  
Company  

Documents list

Next action

Timeline

Benefits:

No page reload  
Fewer clicks  

---------------------------------------------------------------------

16. TIMELINE SYSTEM

Chronological event log.

Example:

10 Mar Candidate created  
11 Mar Documents requested  
12 Mar Passport uploaded  
13 Mar Code95 uploaded  
15 Mar Permit ordered  

Purpose:

Instant context.

---------------------------------------------------------------------

17. DOCUMENT INTELLIGENCE

HostFlow advantage over generic CRM.

Features:

Document completeness  
Expiration tracking  
Missing document alerts  
Compliance status  

Example indicators:

Documents 3 / 5  
Code95 missing  
Passport expiring  

---------------------------------------------------------------------

18. DASHBOARD DESIGN

Maximum 6–8 widgets.

Example widgets:

Candidates in pipeline  
Drivers hired  
Waiting documents  
Permits processing  
Top recruiter  
Top client  

Chart types:

Bar chart  
Line chart  
Pipeline chart  

---------------------------------------------------------------------

19. SEARCH SYSTEM

Global search must support:

Candidate name  
Phone number  
Company  
Email  
Document number  

---------------------------------------------------------------------

20. COMPLIANCE FEATURES

HostFlow should include:

Permit tracking  
Visa status  
Driver certification monitoring  
Document expiry alerts  

Examples:

Code95 expiration  
Permit delays  
Missing residence permit  

---------------------------------------------------------------------

21. CANDIDATE READINESS SCORE

Calculated from:

Document completeness  
Permit status  
Stage progress  
Compliance checks  

Example:

Candidate readiness 85 %

---------------------------------------------------------------------

22. RECRUITMENT METRICS

Recruiter performance

Candidates managed  
Interviews scheduled  
Drivers hired  

Pipeline metrics

Stage conversion  
Average stage time  
Drop-off reasons  

Client metrics

Drivers placed per client  
Vacancy conversion  
Time to hire  

---------------------------------------------------------------------

23. UX FLOW EXAMPLE

Open Candidates

View pipeline summary

Click stage

Table filters

Open candidate

Upload document

Stage updated

---------------------------------------------------------------------

24. PRODUCT POSITIONING

HostFlow combines three systems:

ATS  
CRM  
Compliance platform

Pipedrive is a CRM only.

HostFlow advantage comes from specialization.

Key differentiators:

Document intelligence  
Visa tracking  
Permit workflow  
Driver compliance  
Recruitment pipeline automation

---------------------------------------------------------------------

25. HOSTFLOW IMPLEMENTATION NOTES (code + this doc)

Product principles in §2–§4 above target **active** pipeline work (“what’s next”, document gates, reminders).

For candidates in **pipeline-completed** canonical stages — **`employed`**, **`probation_ok`**, **`rejected`**, **`declined`** — the product treats the case as **closed operationally**: document checklist does not block the stage rail, **`risk_model_v1`** scores are zeroed for those rows (list/detail/work-panel may skip heavy DB scoring when the stored stage is terminal), **next-action** / journey hints do not push “move forward”, and ops aggregates (goals, no-next-action lists, hourly risk baselines) exclude them unless explicitly filtered. Код: например **`constants/stages.py`** (`PIPELINE_COMPLETED_STAGE_CODES`, `is_pipeline_completed_stage`), **`candidate_risk_stage_gate`**, **`hiring_pipeline_gates`**, UI **`candidateStageDocPolicy`** / **`CandidateCard`**.

**`docs/SSOT.md`** — только **правила разработки и открытый бэклог**; детали домена и история релизов — **git**, этот **`pipe.md`**, модульные **`docs/specs/**`**. **`docs/pipedesign.md`** — маркетинг / IA / токены.

---------------------------------------------------------------------

END OF DOCUMENT