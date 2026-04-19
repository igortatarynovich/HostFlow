import { useCallback, useMemo, useState } from 'react'
import type { AdminUser, UserRole } from '../../api/types'
import { useI18n } from '../../i18n'

type ActionKey = 'role' | 'activate' | 'deactivate' | 'revoke' | 'audit'

interface UserTableProps {
  users: AdminUser[]
  onChangeRole: (userId: string, role: UserRole) => Promise<void>
  onToggleActive: (userId: string, active: boolean) => Promise<void>
  onRevokeRefresh: (userId: string) => Promise<void>
  onShowAudit: (userId: string, email: string) => void
  onSelect?: (user: AdminUser) => void
  selectedUserId?: string | null
  className?: string
}

const ROLE_OPTIONS: UserRole[] = ['administrator', 'supervisor', 'recruiter', 'client_manager', 'client_processor', 'viewer']
const ROLE_LABELS: Record<UserRole, string> = {
  administrator: 'app.admin.users.roles.administrator',
  supervisor: 'app.admin.users.roles.supervisor',
  recruiter: 'app.admin.users.roles.recruiter',
  client_manager: 'app.admin.users.roles.client_manager',
  client_processor: 'app.admin.users.roles.client_processor',
  viewer: 'app.admin.users.roles.viewer',
}

const STATUS_LABELS: Record<string, string> = {
  invited: 'app.admin.users.table.status.invited',
  inactive: 'app.admin.users.table.status.inactive',
  active: 'app.admin.users.table.status.active',
}

export function UserTable({
  users,
  onChangeRole,
  onToggleActive,
  onRevokeRefresh,
  onShowAudit,
  onSelect,
  selectedUserId,
  className,
}: UserTableProps) {
  const [pendingMap, setPendingMap] = useState<Record<string, ActionKey | null>>({})
  const { t } = useI18n()
  const notAvailableLabel = t('common.labels.not_available')

  const formatDateValue = useCallback(
    (value?: string | null) => {
      if (!value) return notAvailableLabel
      const dt = new Date(value)
      if (Number.isNaN(dt.getTime())) return value ?? notAvailableLabel
      return dt.toLocaleString()
    },
    [notAvailableLabel],
  )

  const sortedUsers = useMemo(() => {
    const roleOrder: Record<string, number> = {
      administrator: 0,
      supervisor: 1,
      recruiter: 2,
      viewer: 3,
    }
    return [...users].sort((a, b) => {
      const aOrder = roleOrder[a.role] ?? 9
      const bOrder = roleOrder[b.role] ?? 9
      if (aOrder !== bOrder) return aOrder - bOrder
      return (a.email || '').localeCompare(b.email || '')
    })
  }, [users])

  async function runAction(
    key: string,
    actionKey: ActionKey,
    cb: () => Promise<void>,
  ) {
    setPendingMap((prev) => ({ ...prev, [key]: actionKey }))
    try {
      await cb()
    } finally {
      setPendingMap((prev) => {
        const next = { ...prev }
        delete next[key]
        return next
      })
    }
  }

  return (
    <div className={['overflow-auto border border-slate-200 rounded-lg bg-white', className].filter(Boolean).join(' ')}>
      <table className="min-w-full divide-y divide-slate-200">
        <thead className="bg-slate-50">
          <tr className="text-left text-sm font-semibold text-slate-600">
            <th className="px-4 py-3">{t('app.admin.users.table.columns.email')}</th>
            <th className="px-4 py-3">{t('app.admin.users.table.columns.role')}</th>
            <th className="px-4 py-3">{t('app.admin.users.table.columns.status')}</th>
            <th className="px-4 py-3">{t('app.admin.users.table.columns.invited_at')}</th>
            <th className="px-4 py-3">{t('app.admin.users.table.columns.actions')}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 text-sm">
          {sortedUsers.map((user) => {
            const key = user.user_id || user.invite_id || user.email
            const pending = pendingMap[key]
            const isInviteOnly = !user.user_id
            const roleValue = (user.role ?? 'viewer') as UserRole
            const statusKey = STATUS_LABELS[user.status ?? ''] ?? STATUS_LABELS.active
            const statusLabel = t(statusKey, { defaultValue: user.status ?? 'active' })
            const isSelected = Boolean(selectedUserId && user.user_id && selectedUserId === user.user_id)
            const rowClasses = [
              'transition-colors',
              onSelect && user.user_id ? 'cursor-pointer' : '',
              isSelected ? 'bg-indigo-50' : '',
              !isSelected ? 'hover:bg-indigo-50/60' : '',
            ]
              .filter(Boolean)
              .join(' ')

            return (
              <tr
                key={key}
                className={rowClasses}
                onClick={() => {
                  if (onSelect && user.user_id) {
                    onSelect(user)
                  }
                }}
              >
                <td className="px-4 py-3">
                  <div className="font-medium text-slate-900">{user.email}</div>
                  <div className="text-xs text-slate-500">
                    {user.full_name || user.short_id || notAvailableLabel}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {isInviteOnly ? (
                    <span className="inline-flex items-center rounded bg-indigo-50 px-2 py-1 text-xs text-indigo-600">
                      {t(ROLE_LABELS[roleValue] ?? roleValue)}
                    </span>
                  ) : (
                    <select
                      className="input text-sm"
                      value={roleValue}
                      disabled={!!pending}
                      onClick={(event) => event.stopPropagation()}
                      onChange={(ev) =>
                        runAction(user.user_id!, 'role', () =>
                          onChangeRole(user.user_id!, ev.target.value as UserRole),
                        )
                      }
                    >
                      {ROLE_OPTIONS.map((option) => (
                        <option key={option} value={option}>
                          {t(ROLE_LABELS[option])}
                        </option>
                      ))}
                    </select>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span
                      className={[
                        'inline-flex h-2 w-2 rounded-full',
                        user.status === 'active'
                          ? 'bg-emerald-500'
                          : user.status === 'invited'
                          ? 'bg-amber-500'
                          : 'bg-slate-400',
                      ].join(' ')}
                    />
                    <span>{statusLabel}</span>
                  </div>
                  {user.invite_expires_at && (
                    <div className="text-xs text-slate-400">
                      {t('app.admin.users.table.invite_expires_prefix', {
                        values: { date: formatDateValue(user.invite_expires_at) },
                      })}
                    </div>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="text-xs text-slate-500">{formatDateValue(user.invited_at)}</div>
                </td>
                <td className="px-4 py-3">
                  {isInviteOnly ? (
                    <span className="text-xs text-slate-400">
                      {t('app.admin.users.table.pending_registration')}
                    </span>
                  ) : (
                    <div className="flex flex-wrap items-center gap-2">
                      <button
                        type="button"
                        className="btn-secondary"
                        disabled={!!pending}
                        onClick={(event) => {
                          event.stopPropagation()
                          runAction(
                            user.user_id!,
                            user.is_active ? 'deactivate' : 'activate',
                            () => onToggleActive(user.user_id!, !user.is_active),
                          )
                        }}
                      >
                        {pending === 'activate' || pending === 'deactivate'
                          ? '…'
                          : user.is_active
                          ? t('app.admin.users.table.actions.deactivate')
                          : t('app.admin.users.table.actions.activate')}
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        disabled={!!pending}
                        onClick={(event) => {
                          event.stopPropagation()
                          runAction(user.user_id!, 'revoke', () => onRevokeRefresh(user.user_id!))
                        }}
                      >
                        {pending === 'revoke'
                          ? '…'
                          : t('app.admin.users.table.actions.revoke_refresh')}
                      </button>
                      <button
                        type="button"
                        className="btn-secondary"
                        onClick={(event) => {
                          event.stopPropagation()
                          onShowAudit(user.user_id!, user.email)
                        }}
                        disabled={pending === 'audit'}
                      >
                        {t('app.admin.users.table.actions.audit')}
                      </button>
                    </div>
                  )}
                </td>
              </tr>
            )
          })}
          {sortedUsers.length === 0 && (
            <tr>
              <td className="px-4 py-6 text-center text-sm text-slate-500" colSpan={5}>
                {t('app.admin.users.table.empty')}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
