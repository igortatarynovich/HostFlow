import type { FormEvent } from 'react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { listCompanies } from '../../api/client'
import { grantCompanyAccess, listCompanyAccess, revokeCompanyAccess } from '../../api/access'
import { listAdminUsers } from '../../api/users'
import type { AdminUser, Company, CompanyAccessEntry } from '../../api/types'
import { usePermissions } from '../../hooks/usePermissions'

interface AccessFormState {
  userId: string
  canEdit: boolean
}

function toCompanyOptions(data: any): Company[] {
  const items: Company[] = []
  const source = Array.isArray(data?.items) ? data.items : Array.isArray(data) ? data : []
  for (const item of source) {
    const id = item?.id || item?.uuid || item?.company_id
    if (!id) continue
    items.push({
      id,
      name: item?.name || item?.title || id,
      country: item?.country ?? null,
      city: item?.city ?? null,
    })
  }
  return items
}

export default function CompanyAccessPage() {
  const { can } = usePermissions()
  const canManage = can('admin.companyAcl')

  const [companies, setCompanies] = useState<Company[]>([])
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>('')
  const [accessList, setAccessList] = useState<CompanyAccessEntry[]>([])
  const [loadingAccess, setLoadingAccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [allUsers, setAllUsers] = useState<AdminUser[]>([])
  const [form, setForm] = useState<AccessFormState>({ userId: '', canEdit: false })
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!canManage) return
    const loadInitial = async () => {
      try {
        const [companiesResp, usersResp] = await Promise.all([
          listCompanies({ limit: 500 }),
          listAdminUsers(),
        ])
        const companyItems = toCompanyOptions(companiesResp)
        setCompanies(companyItems)
        if (companyItems.length > 0) {
          setSelectedCompanyId(companyItems[0].id)
        }
        setAllUsers(Array.isArray(usersResp) ? usersResp.filter((user) => !!user.user_id) : [])
      } catch (err) {
        console.error('[CompanyAccessPage] initial load failed', err)
        setError('Не удалось загрузить исходные данные')
      }
    }
    void loadInitial()
  }, [canManage])

  const availableUsers = useMemo(() => {
    return allUsers.filter((user) => user.user_id && user.status !== 'invited')
  }, [allUsers])

  const loadAccess = useCallback(
    async (companyId: string) => {
      if (!companyId) return
      setLoadingAccess(true)
      setError(null)
      try {
        const data = await listCompanyAccess(companyId)
        setAccessList(Array.isArray(data) ? data : [])
      } catch (err) {
        console.error('[CompanyAccessPage] access load failed', err)
        setError('Не удалось загрузить список доступа')
      } finally {
        setLoadingAccess(false)
      }
    },
    [],
  )

  useEffect(() => {
    if (selectedCompanyId) {
      void loadAccess(selectedCompanyId)
    }
  }, [selectedCompanyId, loadAccess])

  const handleGrant = useCallback(
    async (event: FormEvent) => {
      event.preventDefault()
      if (!selectedCompanyId || !form.userId) return
      setSaving(true)
      setError(null)
      try {
        await grantCompanyAccess(selectedCompanyId, {
          user_id: form.userId,
          can_edit: form.canEdit,
        })
        setForm({ userId: '', canEdit: false })
        await loadAccess(selectedCompanyId)
      } catch (err) {
        console.error('[CompanyAccessPage] grant failed', err)
        setError('Не удалось выдать доступ компании')
      } finally {
        setSaving(false)
      }
    },
    [selectedCompanyId, form, loadAccess],
  )

  const handleToggle = useCallback(
    async (entry: CompanyAccessEntry) => {
      if (!selectedCompanyId) return
      setSaving(true)
      setError(null)
      try {
        if (!entry.user_id) {
          throw new Error('Нет user_id у записи доступа');
        }
        await grantCompanyAccess(selectedCompanyId, {
          user_id: entry.user_id,
          can_edit: !entry.can_edit,
        })
        await loadAccess(selectedCompanyId)
      } catch (err) {
        console.error('[CompanyAccessPage] toggle failed', err)
        setError('Не удалось обновить права доступа')
      } finally {
        setSaving(false)
      }
    },
    [selectedCompanyId, loadAccess],
  )

  const handleRevoke = useCallback(
    async (entry: CompanyAccessEntry) => {
      if (!selectedCompanyId) return
      if (!entry.user_id) {
        setError('У записи нет user_id');
        return;
      }
      if (!window.confirm(`Отозвать доступ у ${entry.email}?`)) return
      setSaving(true)
      setError(null)
      try {
        await revokeCompanyAccess(selectedCompanyId, entry.user_id)
        await loadAccess(selectedCompanyId)
      } catch (err) {
        console.error('[CompanyAccessPage] revoke failed', err)
        setError('Не удалось отозвать доступ')
      } finally {
        setSaving(false)
      }
    },
    [selectedCompanyId, loadAccess],
  )

  if (!canManage) {
    return (
      <div className="rounded border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
        У вас нет доступа к управлению ACL компаний.
      </div>
    )
  }

  if (companies.length === 0) {
    return <div className="text-sm text-gray-600">Нет компаний для настройки доступа.</div>
  }

  const selectedCompany = companies.find((company) => company.id === selectedCompanyId)

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Доступ к компаниям</h1>
          {selectedCompany && (
            <p className="text-sm text-gray-500">Компания: {selectedCompany.name}</p>
          )}
        </div>
        <select
          className="input w-full max-w-sm"
          value={selectedCompanyId}
          onChange={(event) => setSelectedCompanyId(event.target.value)}
        >
          {companies.map((company) => (
            <option key={company.id} value={company.id}>
              {company.name}
            </option>
          ))}
        </select>
      </header>

      {error && <div className="rounded border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">{error}</div>}

      <section className="rounded-lg border border-gray-200 bg-white p-6 space-y-3">
        <h2 className="text-lg font-semibold text-gray-900">Текущий доступ</h2>
        {loadingAccess ? (
          <div className="text-sm text-gray-500">Загрузка…</div>
        ) : accessList.length === 0 ? (
          <div className="text-sm text-gray-500">Для этой компании пока нет назначенных пользователей.</div>
        ) : (
          <ul className="space-y-2 text-sm">
            {accessList.map((entry) => (
              <li key={entry.user_id} className="flex flex-wrap items-center justify-between gap-2 rounded border border-gray-100 px-3 py-2">
                <div>
                  <div className="font-medium text-gray-900">{entry.email}</div>
                  <div className="text-xs text-gray-500">
                    Роль: {entry.role} · Права: {entry.can_edit ? 'редактирование' : 'просмотр'}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    className="btn-secondary text-xs"
                    disabled={saving}
                    onClick={() => void handleToggle(entry)}
                  >
                    {entry.can_edit ? 'Только просмотр' : 'Разрешить правки'}
                  </button>
                  <button
                    type="button"
                    className="btn-ghost text-xs"
                    disabled={saving}
                    onClick={() => void handleRevoke(entry)}
                  >
                    Удалить
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-gray-200 bg-white p-6 space-y-4">
        <h2 className="text-lg font-semibold text-gray-900">Выдать доступ</h2>
        <form className="space-y-3" onSubmit={handleGrant}>
          <label className="block text-sm">
            <span className="label">Пользователь</span>
            <select
              className="input w-full"
              value={form.userId}
              onChange={(event) => setForm((prev) => ({ ...prev, userId: event.target.value }))}
              required
            >
              <option value="">Выберите пользователя</option>
              {availableUsers.map((user) => (
                <option key={user.user_id} value={user.user_id!}>
                  {user.email} ({user.role})
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.canEdit}
              onChange={(event) => setForm((prev) => ({ ...prev, canEdit: event.target.checked }))}
            />
            <span>Разрешить редактирование данных компании</span>
          </label>

          <button type="submit" className="btn-primary" disabled={saving || !form.userId}>
            {saving ? 'Сохраняем…' : 'Выдать доступ'}
          </button>
        </form>
      </section>
    </div>
  )
}
