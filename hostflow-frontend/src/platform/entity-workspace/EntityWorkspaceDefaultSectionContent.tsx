import type { EntityPassport } from '../entity-model'
import type { EntityWorkspaceSectionId } from './types'

type SectionContentProps = {
  sectionId: EntityWorkspaceSectionId
  passport: EntityPassport
}

/** Generic section body from passport slices — no module-specific logic. */
export function EntityWorkspaceDefaultSectionContent({ sectionId, passport }: SectionContentProps) {
  const s = passport.sections

  switch (sectionId) {
    case 'overview':
      return (
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Объект</dt>
            <dd className="mt-1 font-medium text-slate-900">{s.identity.title}</dd>
          </div>
          {s.identity.shortId ? (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">ID</dt>
              <dd className="mt-1 text-slate-800">{s.identity.shortId}</dd>
            </div>
          ) : null}
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Процесс</dt>
            <dd className="mt-1 text-slate-800">{s.state.processLabel}</dd>
          </div>
          {s.state.stageLabel ? (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Этап</dt>
              <dd className="mt-1 text-slate-800">{s.state.stageLabel}</dd>
            </div>
          ) : null}
          {s.ownership.managerLabel ? (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-slate-500">Ответственный</dt>
              <dd className="mt-1 text-slate-800">{s.ownership.managerLabel}</dd>
            </div>
          ) : null}
        </dl>
      )

    case 'contacts':
      return (
        <div className="space-y-3 text-sm">
          {s.contacts.displayName ? <p className="font-medium text-slate-900">{s.contacts.displayName}</p> : null}
          {s.contacts.citizenship ? <p className="text-slate-600">Гражданство: {s.contacts.citizenship}</p> : null}
          <ul className="space-y-2">
            {s.contacts.channels.map((ch) => (
              <li key={`${ch.kind}-${ch.value}`}>
                {ch.href ? (
                  <a href={ch.href} className="font-medium text-brand-700 hover:underline">
                    {ch.display || ch.value}
                  </a>
                ) : (
                  <span className="text-slate-800">{ch.display || ch.value}</span>
                )}
                <span className="ml-2 text-xs uppercase text-slate-400">{ch.kind}</span>
              </li>
            ))}
          </ul>
        </div>
      )

    case 'documents':
      return (
        <div className="space-y-3 text-sm">
          {s.documents.readinessLabel ? (
            <p>
              <span className="text-slate-500">Готовность: </span>
              <span className="font-medium text-slate-900">{s.documents.readinessLabel}</span>
            </p>
          ) : null}
          {s.documents.blockersSummary ? (
            <p className="rounded-lg border border-amber-200 bg-amber-50/60 px-3 py-2 text-amber-900">{s.documents.blockersSummary}</p>
          ) : null}
          {s.documents.missing.length ? (
            <div>
              <p className="text-xs font-semibold uppercase text-slate-500">Не хватает</p>
              <ul className="mt-1 list-disc pl-5 text-slate-700">
                {s.documents.missing.map((code) => (
                  <li key={code}>{code}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      )

    case 'timeline':
      return (
        <ul className="space-y-3 text-sm">
          {s.timeline.items.length === 0 ? (
            <li className="text-slate-500">Нет событий</li>
          ) : (
            s.timeline.items.map((ev) => (
              <li key={ev.id} className="border-l-2 border-slate-200 pl-3">
                <p className="font-medium text-slate-900">{ev.title}</p>
                {ev.description ? <p className="text-slate-600">{ev.description}</p> : null}
                <p className="text-xs text-slate-400">{ev.at}</p>
              </li>
            ))
          )}
        </ul>
      )

    case 'relations':
      return (
        <ul className="space-y-2 text-sm">
          {s.relations.items.length === 0 ? (
            <li className="text-slate-500">Нет связей</li>
          ) : (
            s.relations.items.map((rel) => (
              <li key={rel.id}>
                {rel.href ? (
                  <a href={rel.href} className="font-medium text-brand-700 hover:underline">
                    {rel.label}
                  </a>
                ) : (
                  <span className="font-medium text-slate-900">{rel.label}</span>
                )}
                <span className="ml-2 text-xs uppercase text-slate-400">{rel.kind}</span>
              </li>
            ))
          )}
        </ul>
      )

    case 'tasks':
      return (
        <ul className="space-y-2 text-sm">
          {s.tasks.items.length === 0 ? (
            <li className="text-slate-500">Нет задач</li>
          ) : (
            s.tasks.items.map((task) => (
              <li key={task.id} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
                <p className="font-medium text-slate-900">{task.title}</p>
                {task.dueAt ? <p className="text-xs text-slate-500">{task.dueAt}</p> : null}
              </li>
            ))
          )}
        </ul>
      )

    case 'outcome':
      return s.outcome ? (
        <div className="space-y-2 text-sm">
          <p className="text-lg font-bold text-slate-900">{s.outcome.title}</p>
          {s.outcome.body ? <p className="text-slate-600">{s.outcome.body}</p> : null}
          {s.outcome.why ? <p className="border-l-2 border-slate-300 pl-3 text-slate-700">{s.outcome.why}</p> : null}
          {s.outcome.ownerLabel ? <p className="text-slate-600">Владелец: {s.outcome.ownerLabel}</p> : null}
          {s.outcome.whenLabel ? <p className="text-slate-500">{s.outcome.whenLabel}</p> : null}
        </div>
      ) : (
        <p className="text-sm text-slate-500">Процесс активен</p>
      )

    default:
      return <p className="text-sm text-slate-500">Раздел не настроен</p>
  }
}
