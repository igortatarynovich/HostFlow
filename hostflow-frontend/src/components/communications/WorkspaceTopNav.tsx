import clsx from 'clsx'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'

type WorkspaceSection = 'calendar' | 'tasks' | 'messages' | 'email' | null

type Props = {
  active: WorkspaceSection
}

const ITEMS: Array<{ key: Exclude<WorkspaceSection, null>; to: string; labelKey: string; defaultLabel: string }> = [
  { key: 'calendar', to: '/app/calendar', labelKey: 'app.nav.items.calendar', defaultLabel: 'Calendar' },
  { key: 'tasks', to: '/app/tasks', labelKey: 'app.nav.items.tasks', defaultLabel: 'Tasks' },
  { key: 'messages', to: '/app/inbox?channel=messages', labelKey: 'app.nav.items.messages', defaultLabel: 'Messages' },
  { key: 'email', to: '/app/inbox?channel=email', labelKey: 'app.nav.items.email', defaultLabel: 'Email' },
]

export default function WorkspaceTopNav({ active }: Props) {
  const { t } = useI18n()
  const visibleKeys: Array<Exclude<WorkspaceSection, null>> =
    active === 'messages' || active === 'email' || active === null
      ? ['messages', 'email']
      : ['calendar', 'tasks']

  return (
    <div className="sticky top-0 z-20 w-full rounded-none border-x-0 border-t-0 border-b border-slate-200 bg-white/95 p-2 shadow-none backdrop-blur">
      <div className="flex flex-nowrap items-center gap-2 overflow-x-auto pb-1">
        {ITEMS.filter((item) => visibleKeys.includes(item.key)).map((item) => (
          <Link
            key={item.key}
            to={item.to}
            className={clsx(
              'shrink-0 whitespace-nowrap rounded border px-3 py-1.5 text-sm',
              active === item.key
                ? 'border-slate-900 bg-slate-900 text-white'
                : 'border-slate-300 text-slate-700 hover:bg-slate-50',
            )}
          >
            {t(item.labelKey, { defaultValue: item.defaultLabel })}
          </Link>
        ))}
      </div>
    </div>
  )
}
