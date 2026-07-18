# Acquisition / Campaigns and Intake: охват платформенной capability

Нормативное решение — **[`ADR-024`](../specs/architecture/ADR-024-acquisition-campaigns-intake-routing.md)**.

## Канон

> HostFlow — **система управления ростом**: Growth → Intake → Operations → Intelligence ↺ Growth.

> Привлечение спроса **отделено** от исполнения бизнес-процессов.

> **CampaignTemplate** — готовый playbook / экспертиза (после V1).  
> **Campaign** — долгоживущая инициатива.  
> **Flight / CampaignRun** — конкретная волна (V1 = ровно один).

> **Goal Type + Primary KPI** — зачем и чем измеряем (не плоский enum Hire/Sales/Brand).  
> **`route_intent`** — что создать во Intake.  
> **Outcome** — измеримый progress.

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
| **Growth** | Привести нужных людей (Templates, Campaigns, Flights, Audiences, Channels, Assets, Forms, Attribution) |
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
    │     ├── Forms (links)
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

1. **3A** — Campaign + Goal Type + Primary KPI + Target + reserved CampaignRun (**не** Template)  
2. **3B** — Form + Intake Source  
3. **3C** — routing → Application | Inquiry  
4. **3D** — Result → Flight → Campaign + Outcome progress  
5. **3E** — Timeline + automation events  

V1 vertical:

```text
Campaign + Goal Type + Primary KPI → Target → Flight(1) → Form → …
  → Result attribution → Outcome progress
```

**CampaignTemplate** catalog + instantiate — после V1 (ориентир V2). Multi-Flight UX — тоже после V1.

## Anti-scope (Stage 3A / V1)

- Не Marketing product / `marketing.*`  
- Не Template catalog в 3A  
- Не multi-Flight UX в V1  
- Не Goal как плоский enum  
- Не Goal = `route_intent`  
- Не Form exclusive child / typed FK на Campaign / SoT Candidate в Acquisition  
