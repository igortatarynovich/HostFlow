import clsx from 'clsx'
import { Link } from 'react-router-dom'
import { useI18n } from '../../i18n'

type WorkspaceSection = 'calendar' | 'planner' | 'reminders' | 'messages' | 'email' | null
  | 'activities'
  | 'my_availability'
  | 'team_availability'

type Props = {
  active: WorkspaceSection
}

const ITEMS: Array<{ key: Exclude<WorkspaceSection, null>; to: string; labelKey: string; defaultLabel: string }> = [
  { key: 'calendar', to: '/app/calendar', labelKey: 'app.nav.items.calendar', defaultLabel: 'Calendar' },
  { key: 'planner', to: '/app/planner', labelKey: 'app.nav.items.planner', defaultLabel: 'Planner' },
  { key: 'activities', to: '/app/activities', labelKey: 'app.nav.items.activities', defaultLabel: 'Activities' },
  { key: 'reminders', to: '/app/reminders', labelKey: 'app.nav.items.reminders', defaultLabel: 'Reminders' },
  { key: 'messages', to: '/app/messages', labelKey: 'app.nav.items.messages', defaultLabel: 'Messages' },
  { key: 'email', to: '/app/email', labelKey: 'app.nav.items.email', defaultLabel: 'Email' },
  { key: 'my_availability', to: '/app/my-availability', labelKey: 'app.nav.items.my_availability', defaultLabel: 'My availability' },
  { key: 'team_availability', to: '/app/team-availability', labelKey: 'app.nav.items.team_availability', defaultLabel: 'Team availability' },
]

export default function WorkspaceTopNav({ active }: Props) {
  const { t } = useI18n()
  const visibleKeys: Array<Exclude<WorkspaceSection, null>> =
    active === 'messages' || active === 'email' || active === null
      ? ['messages', 'email']
      : ['calendar', 'planner', 'activities', 'reminders', 'my_availability', 'team_availability']

  return (
    <div className="sticky top-2 z-20 rounded-lg border border-slate-200 bg-white/95 p-2 shadow-sm backdrop-blur">
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
