# Acquisition / Campaigns and Intake: охват платформенной capability

Нормативное решение — **[`ADR-024`](../specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md)**.

## Канон

> HostFlow — **система управления ростом**: Growth → Intake → Operations → Intelligence ↺ Growth.

> **Intake spine:** `Endpoint → Submission → Routing → Decision → Business Entity`

> Привлечение спроса **отделено** от исполнения бизнес-процессов.

> **Campaign → Endpoint → Submission** (не Campaign → Form).  
> Campaign отвечает за Attribution, Routing Context, Intent, Source.

> **CampaignTemplate** — готовый playbook / экспертиза (после V1).  
> **Campaign** — долгоживущая инициатива.  
> **Flight / CampaignRun** — конкретная волна (V1 = ровно один).

> **Goal Type + Primary KPI** — зачем и чем измеряем.  
> **`route_intent`** — что создать во Intake.  
> **Outcome** — измеримый progress.

> **Routing once** при создании Lead; continuation Submissions наследуют context.

```text
Template → Campaign → Flight → Results → Outcomes
```

```text
Acquisition creates demand flow;
destination modules own resulting business objects.
```

## Четыре уровня

| Уровень | Задача |
|---------|--------|
| **Growth** | Привести нужных людей (Templates, Campaigns, Flights, Audiences, Channels, Assets, **Endpoints**, Attribution) |
| **Intake** | Распределить обращения (Sources, Submissions, Routing, Inbox, Dedup, Screening) |
| **Operations** | Создать ценность (Recruitment, HR, Sales, Fleet, Finance) |
| **Intelligence** | Улучшать решения, следующий Flight / Template |

## Структура Campaign Manager

```text
CampaignTemplate                 ← playbook (post-V1)
└── Campaign
    ├── Goal Type + Primary KPI
    ├── Targets
    ├── Flights / CampaignRuns
    │     ├── Channels
    │     ├── Audiences
    │     ├── Assets
    │     ├── Endpoints (links; HostFlow Form / Meta / API / …)
    │     └── Budget
    ├── Attribution / Analytics
    ├── Timeline
    ├── Results
    └── Outcomes
```

## Form / Audience

```text
Campaign / Flight ──uses──► Form
Campaign → Audience(s) → Flight → Channels
```

## Target / Context / Result + Goal

| Target | Context | Result | Goal Type | Primary KPI |
|--------|---------|--------|-----------|-------------|
| Что продвигаем | Для кого | Что создаётся | Класс цели | Главный критерий успеха |

Две кампании с Goal Type = Hiring могут отличаться Primary KPI: Cost per Hire vs Hires.

## Delivery

После **production cutover**:

1. **3A** ✅ — Campaign + Goal Type + Primary KPI + Target + reserved CampaignRun (**не** Template)  
2. **3B** ✅ — Endpoint binding (V1: Form + Intake Source specializations; canon = CampaignRun ↔ Endpoint)  
3. **3C** ✅ — routing → Application | Inquiry (Submission before Decision Layer; routing once per Lead)  
4. **3D** ✅ — **Epic P COMPLETE** — Result → Outcome → KPI — [`../specs/tasks/acquisition-epic-p-stage-3d.md`](../specs/tasks/acquisition-epic-p-stage-3d.md) · E2E `test_stage_3d_epic_p_contract.py`  
5. **Canonical Input Matrix** ✅ **READY** (design) — [`../specs/architecture/intake-canonical-input-matrix.md`](../specs/architecture/intake-canonical-input-matrix.md) · epic [`../specs/tasks/intake-canonical-input-matrix.md`](../specs/tasks/intake-canonical-input-matrix.md) **ACTIVE** — freeze Source profile → Provider → Published form → `route_intent` → handoff → Destination **before** further routing runtime  
6. **3E** — Timeline + automation events  

**Forms Builder MVP COMPLETE** (P2.1–P2.5). Forms P3 Publish UI **LOCKED**.  
See [`capability-contract.md`](../specs/architecture/capability-contract.md).

V1 vertical:

```text
Campaign → Flight → Endpoint → Submission → Result → Outcome → KPI
```

**CampaignTemplate** catalog + instantiate — после V1 (ориентир V2). Multi-Flight UX — тоже после V1.

## Anti-scope (Stage 3A / V1)

- Не Marketing product / `marketing.*`  
- Не Template catalog в 3A  
- Не multi-Flight UX в V1  
- Не Goal как плоский enum  
- Не Goal = `route_intent`  
- Не Form exclusive child / typed FK на Campaign / SoT Candidate в Acquisition  
- Не зависимость Campaign от Forms internals (только Endpoint → Submission)  
