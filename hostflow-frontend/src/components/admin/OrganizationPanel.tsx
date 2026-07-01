import { useCallback, useMemo, useState, type FormEvent, type ReactElement } from 'react'
import type { AdminUser, ManagerOption } from '../../api/types'
import {
  addOrgUnitMember,
  createOrgUnit,
  deleteOrgUnit,
  exportOrgStructureSnapshot,
  importOrgStructureMerge,
  listOrgUnitMembers,
  patchOrgUnit,
  type OrgUnitTreeNode,
  removeOrgUnitMember,
} from '../../api/orgStructure'
import { useI18n } from '../../i18n'

function findNodeInTree(nodes: OrgUnitTreeNode[], id: string): OrgUnitTreeNode | null {
  for (const n of nodes) {
    if (n.id === id) return n
    if (n.children?.length) {
      const inner = findNodeInTree(n.children, id)
      if (inner) return inner
    }
  }
  return null
}

function collectSubtreeIds(n: OrgUnitTreeNode): Set<string> {
  const s = new Set<string>([n.id])
  for (const c of n.children || []) {
    for (const id of collectSubtreeIds(c)) s.add(id)
  }
  return s
}

type Props = {
  tenantId?: string
  /** All tenant users for «add member» picker */
  users: AdminUser[]
  managerOptions: ManagerOption[]
  tree: OrgUnitTreeNode[]
  treeLoading: boolean
  onReloadTree: () => Promise<void>
}

export function OrganizationPanel({ tenantId, users, managerOptions, tree, treeLoading, onReloadTree }: Props) {
  const { t } = useI18n()
  const opts = useMemo(() => ({ tenantId }), [tenantId])
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const [newName, setNewName] = useState('')
  const [newCode, setNewCode] = useState('')
  const [newParent, setNewParent] = useState<string>('')
  const [newType, setNewType] = useState('department')
  const [newSortOrder, setNewSortOrder] = useState(0)
  const [creating, setCreating] = useState(false)

  const [memberUnitId, setMemberUnitId] = useState<string | null>(null)
  const [members, setMembers] = useState<Record<string, Awaited<ReturnType<typeof listOrgUnitMembers>>>>({})
  const [memberUserId, setMemberUserId] = useState('')
  const [memberBusy, setMemberBusy] = useState(false)

  const [editUnitId, setEditUnitId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')
  const [editCode, setEditCode] = useState('')
  const [editParent, setEditParent] = useState('')
  const [editType, setEditType] = useState('department')
  const [editLeaderId, setEditLeaderId] = useState('')
  const [editSortOrder, setEditSortOrder] = useState(0)
  const [editSaving, setEditSaving] = useState(false)

  const [importBusy, setImportBusy] = useState(false)

  const forbiddenParentIds = useMemo(() => {
    if (!editUnitId) return new Set<string>()
    const node = findNodeInTree(tree, editUnitId)
    return node ? collectSubtreeIds(node) : new Set()
  }, [tree, editUnitId])

  const flatUnits = useMemo(() => {
    const rows: { id: string; label: string }[] = [{ id: '', label: t('app.admin.org.root', { defaultValue: '(root)' }) }]
    const walk = (nodes: OrgUnitTreeNode[], depth: number) => {
      for (const n of nodes) {
        rows.push({ id: n.id, label: `${'\u2014 '.repeat(depth)}${n.name}` })
        if (n.children?.length) walk(n.children, depth + 1)
      }
    }
    walk(tree, 0)
    return rows
  }, [tree, t])

  const parentOptionsForEdit = useMemo(() => {
    return flatUnits.filter((o) => !o.id || !forbiddenParentIds.has(o.id))
  }, [flatUnits, forbiddenParentIds])

  const startEdit = (n: OrgUnitTreeNode) => {
    setEditUnitId(n.id)
    setEditName(n.name)
    setEditCode(n.code ?? '')
    setEditParent(n.parent_id ?? '')
    setEditType(n.unit_type || 'department')
    setEditLeaderId(n.leader_user_id ?? '')
    setEditSortOrder(Number.isFinite(n.sort_order) ? n.sort_order : 0)
    setError(null)
  }

  const cancelEdit = () => {
    setEditUnitId(null)
    setEditName('')
    setEditCode('')
    setEditParent('')
    setEditType('department')
    setEditLeaderId('')
    setEditSortOrder(0)
  }

  const onSaveEdit = async (ev: FormEvent) => {
    ev.preventDefault()
    if (!editUnitId) return
    const name = editName.trim()
    if (!name) return
    setEditSaving(true)
    setError(null)
    try {
      await patchOrgUnit(
        editUnitId,
        {
          name,
          code: editCode.trim() || null,
          parent_id: editParent || null,
          unit_type: editType,
          leader_user_id: editLeaderId || null,
          sort_order: editSortOrder,
        },
        opts,
      )
      cancelEdit()
      await onReloadTree()
    } catch {
      setError(t('app.admin.org.update_failed', { defaultValue: 'Could not save changes.' }))
    } finally {
      setEditSaving(false)
    }
  }

  const onCreateRoot = async (ev: FormEvent) => {
    ev.preventDefault()
    const name = newName.trim()
    if (!name) return
    setCreating(true)
    setError(null)
    try {
      await createOrgUnit(
        {
          name,
          code: newCode.trim() || null,
          parent_id: newParent || null,
          unit_type: newType || 'department',
          sort_order: newSortOrder,
        },
        opts,
      )
      setNewName('')
      setNewCode('')
      setNewSortOrder(0)
      await onReloadTree()
    } finally {
      setCreating(false)
    }
  }

  const onDeleteUnit = useCallback(
    async (id: string) => {
      if (!window.confirm(t('app.admin.org.delete_confirm', { defaultValue: 'Delete this org unit?' }))) return
      setError(null)
      try {
        await deleteOrgUnit(id, opts)
        setMemberUnitId((cur) => (cur === id ? null : cur))
        await onReloadTree()
      } catch {
        setError(t('app.admin.org.delete_failed', { defaultValue: 'Could not delete (check children / members).' }))
      }
    },
    [opts, t, onReloadTree],
  )

  const openMembers = async (id: string) => {
    setMemberUnitId(id)
    setMemberBusy(true)
    try {
      const rows = await listOrgUnitMembers(id, opts)
      setMembers((m) => ({ ...m, [id]: rows }))
    } finally {
      setMemberBusy(false)
    }
  }

  const onAddMember = async () => {
    if (!memberUnitId || !memberUserId) return
    setMemberBusy(true)
    try {
      await addOrgUnitMember(memberUnitId, { user_id: memberUserId, role_in_unit: 'member' }, opts)
      setMemberUserId('')
      const rows = await listOrgUnitMembers(memberUnitId, opts)
      setMembers((m) => ({ ...m, [memberUnitId]: rows }))
      await onReloadTree()
    } finally {
      setMemberBusy(false)
    }
  }

  const onRemoveMember = async (unitId: string, userId: string) => {
    setMemberBusy(true)
    try {
      await removeOrgUnitMember(unitId, userId, opts)
      const rows = await listOrgUnitMembers(unitId, opts)
      setMembers((m) => ({ ...m, [unitId]: rows }))
      await onReloadTree()
    } finally {
      setMemberBusy(false)
    }
  }

  function renderNode(n: OrgUnitTreeNode, depth: number): ReactElement {
    const open = expanded[n.id] !== false
    const leaderOpt = n.leader_user_id ? managerOptions.find((m) => m.id === n.leader_user_id) : undefined
    const leaderLabel = leaderOpt ? leaderOpt.label || leaderOpt.full_name || leaderOpt.email : null
    return (
      <li key={n.id} className="text-sm">
        <div className="flex flex-wrap items-center gap-2 py-1" style={{ paddingLeft: depth * 12 }}>
          {n.children?.length ? (
            <button
              type="button"
              className="btn text-slate-400 hover:text-slate-700 w-5"
              aria-expanded={open}
              onClick={() => setExpanded((e) => ({ ...e, [n.id]: !open }))}
            >
              {open ? '\u25bc' : '\u25b6'}
            </button>
          ) : (
            <span className="inline-block w-5" />
          )}
          <span className="font-medium text-slate-900">{n.name}</span>
          {n.code ? <span className="text-xs text-slate-400 font-mono">[{n.code}]</span> : null}
          <span className="text-xs text-slate-500">({n.unit_type})</span>
          {n.sort_order !== 0 ? (
            <span className="text-[10px] text-slate-400" title={t('app.admin.org.sort_order', { defaultValue: 'Sort order' })}>
              #{n.sort_order}
            </span>
          ) : null}
          {leaderLabel ? <span className="text-xs text-slate-500">{leaderLabel}</span> : null}
          <button type="button" className="btn text-xs text-brand-700 hover:underline" onClick={() => void openMembers(n.id)}>
            {t('app.admin.org.members', { defaultValue: 'Members' })}
          </button>
          <button type="button" className="btn text-xs text-slate-600 hover:underline" onClick={() => startEdit(n)}>
            {t('app.admin.org.edit', { defaultValue: 'Edit' })}
          </button>
          <button type="button" className="btn text-xs text-rose-700 hover:underline" onClick={() => void onDeleteUnit(n.id)}>
            {t('app.admin.org.delete', { defaultValue: 'Delete' })}
          </button>
        </div>
        {open && n.children?.length ? <ul className="space-y-0">{n.children.map((c) => renderNode(c, depth + 1))}</ul> : null}
      </li>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-semibold text-slate-900">
          {t('app.admin.org.title', { defaultValue: 'Organization' })}
        </h3>
        <p className="mt-1 text-xs text-slate-500">
          {t('app.admin.org.subtitle', {
            defaultValue: 'Departments and teams (tree). Reporting lines are set per user (manager field).',
          })}
        </p>
        <p className="mt-2 text-xs text-slate-600 leading-relaxed border-l-4 border-sky-200 bg-sky-50/70 pl-3 py-2 rounded-r">
          {t('app.admin.org.hint_detail', {
            defaultValue:
              'Org units describe formal departments/teams. The «Supervisor» field on a user is the CRM reporting manager — it does not follow this tree automatically.',
          })}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            className="btn-secondary text-xs"
            disabled={treeLoading}
            onClick={() =>
              void (async () => {
                setError(null)
                try {
                  const data = await exportOrgStructureSnapshot(opts)
                  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
                  const url = URL.createObjectURL(blob)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = 'org-structure-export.json'
                  a.click()
                  URL.revokeObjectURL(url)
                } catch {
                  setError(t('app.admin.org.export_failed', { defaultValue: 'Could not export org structure.' }))
                }
              })()
            }
          >
            {t('app.admin.org.export_json', { defaultValue: 'Export JSON' })}
          </button>
          <label className="btn-secondary text-xs cursor-pointer disabled:opacity-50">
            <input
              type="file"
              accept="application/json,.json"
              className="hidden"
              disabled={importBusy}
              onChange={(ev) => {
                const input = ev.target
                const file = input.files?.[0]
                input.value = ''
                if (!file) return
                void (async () => {
                  setImportBusy(true)
                  setError(null)
                  try {
                    const text = await file.text()
                    const parsed = JSON.parse(text) as unknown
                    if (
                      typeof parsed !== 'object' ||
                      parsed === null ||
                      (parsed as { version?: unknown }).version !== 1 ||
                      !Array.isArray((parsed as { units?: unknown }).units)
                    ) {
                      throw new Error('invalid shape')
                    }
                    await importOrgStructureMerge(parsed as { version: 1; units: Array<Record<string, unknown>> }, opts)
                    await onReloadTree()
                  } catch {
                    setError(t('app.admin.org.import_failed', { defaultValue: 'Invalid file or import failed.' }))
                  } finally {
                    setImportBusy(false)
                  }
                })()
              }}
            />
            {importBusy ? t('common.loading') : t('app.admin.org.import_json', { defaultValue: 'Import JSON…' })}
          </label>
          <span className="text-[11px] text-slate-500 max-w-xl">
            {t('app.admin.org.import_hint', {
              defaultValue: 'Import merges by unique «code» per row; parent_code may reference existing tenant codes.',
            })}
          </span>
        </div>
      </div>

      {error ? <div className="rounded border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-900">{error}</div> : null}

      <form onSubmit={onCreateRoot} className="rounded-lg border border-slate-200 bg-slate-50/80 p-4 space-y-3">
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          {t('app.admin.org.create_unit', { defaultValue: 'Add org unit' })}
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.name', { defaultValue: 'Name' })}</label>
            <input className="input w-full" value={newName} onChange={(e) => setNewName(e.target.value)} required />
          </div>
          <div>
            <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.code', { defaultValue: 'Code' })}</label>
            <input
              className="input w-full font-mono text-sm"
              value={newCode}
              onChange={(e) => setNewCode(e.target.value)}
              placeholder={t('app.admin.org.code_placeholder', { defaultValue: 'Optional internal code' })}
              maxLength={64}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.parent', { defaultValue: 'Parent' })}</label>
            <select className="input w-full" value={newParent} onChange={(e) => setNewParent(e.target.value)}>
              {flatUnits.map((o) => (
                <option key={o.id || 'root'} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.unit_type', { defaultValue: 'Type' })}</label>
            <select className="input w-full" value={newType} onChange={(e) => setNewType(e.target.value)}>
              <option value="division">division</option>
              <option value="department">department</option>
              <option value="team">team</option>
              <option value="cost_center">cost_center</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.sort_order', { defaultValue: 'Sort order' })}</label>
            <input
              type="number"
              className="input w-full"
              value={newSortOrder}
              onChange={(e) => setNewSortOrder(Number(e.target.value) || 0)}
            />
          </div>
        </div>
        <button type="submit" className="btn-primary text-sm" disabled={creating}>
          {creating ? t('common.loading') : t('app.admin.org.submit_create', { defaultValue: 'Create' })}
        </button>
      </form>

      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            {t('app.admin.org.tree', { defaultValue: 'Tree' })}
          </span>
          <button type="button" className="btn text-xs text-brand-700 hover:underline" onClick={() => void onReloadTree()} disabled={treeLoading}>
            {t('app.admin.org.refresh', { defaultValue: 'Refresh' })}
          </button>
        </div>
        {treeLoading ? (
          <p className="text-sm text-slate-500">{t('common.loading')}</p>
        ) : tree.length === 0 ? (
          <p className="text-sm text-slate-500">{t('app.admin.org.empty', { defaultValue: 'No org units yet.' })}</p>
        ) : (
          <ul className="rounded-lg border border-slate-200 bg-white p-3 space-y-0">{tree.map((n) => renderNode(n, 0))}</ul>
        )}
      </div>

      {editUnitId ? (
        <form onSubmit={onSaveEdit} className="rounded-lg border border-amber-200 bg-amber-50/50 p-4 space-y-3">
          <div className="text-xs font-semibold uppercase tracking-wide text-slate-600">
            {t('app.admin.org.edit_title', { defaultValue: 'Edit org unit' })}
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.name', { defaultValue: 'Name' })}</label>
              <input className="input w-full" value={editName} onChange={(e) => setEditName(e.target.value)} required />
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.code', { defaultValue: 'Code' })}</label>
              <input
                className="input w-full font-mono text-sm"
                value={editCode}
                onChange={(e) => setEditCode(e.target.value)}
                placeholder={t('app.admin.org.code_placeholder', { defaultValue: 'Optional internal code' })}
                maxLength={64}
              />
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.parent', { defaultValue: 'Parent' })}</label>
              <select className="input w-full" value={editParent} onChange={(e) => setEditParent(e.target.value)}>
                {parentOptionsForEdit.map((o) => (
                  <option key={o.id || 'root'} value={o.id}>
                    {o.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.unit_type', { defaultValue: 'Type' })}</label>
              <select className="input w-full" value={editType} onChange={(e) => setEditType(e.target.value)}>
                <option value="division">division</option>
                <option value="department">department</option>
                <option value="team">team</option>
                <option value="cost_center">cost_center</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.leader', { defaultValue: 'Leader' })}</label>
              <select className="input w-full" value={editLeaderId} onChange={(e) => setEditLeaderId(e.target.value)}>
                <option value="">{t('app.admin.org.leader_none', { defaultValue: 'No leader' })}</option>
                {managerOptions.map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label || opt.full_name || opt.email}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.sort_order', { defaultValue: 'Sort order' })}</label>
              <input
                type="number"
                className="input w-full"
                value={editSortOrder}
                onChange={(e) => setEditSortOrder(Number(e.target.value) || 0)}
              />
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="submit" className="btn-primary text-sm" disabled={editSaving}>
              {editSaving ? t('common.loading') : t('app.admin.org.save_edit', { defaultValue: 'Save' })}
            </button>
            <button type="button" className="btn-secondary text-sm" disabled={editSaving} onClick={cancelEdit}>
              {t('app.admin.org.cancel_edit', { defaultValue: 'Cancel' })}
            </button>
          </div>
        </form>
      ) : null}

      {memberUnitId ? (
        <div className="rounded-lg border border-indigo-200 bg-indigo-50/40 p-4 space-y-3">
          <div className="text-sm font-semibold text-slate-900">
            {t('app.admin.org.members_title', { defaultValue: 'Members in unit' })}
          </div>
          <div className="flex flex-wrap gap-2 items-end">
            <div className="min-w-[12rem] flex-1">
              <label className="block text-xs text-slate-600 mb-1">{t('app.admin.org.add_member', { defaultValue: 'Add user' })}</label>
              <select className="input w-full" value={memberUserId} onChange={(e) => setMemberUserId(e.target.value)}>
                <option value="">{t('app.admin.org.select_user', { defaultValue: 'Select…' })}</option>
                {users
                  .filter((u) => u.user_id && u.status === 'active')
                  .map((u) => (
                    <option key={u.user_id} value={u.user_id!}>
                      {u.full_name || u.email}
                    </option>
                  ))}
              </select>
            </div>
            <button type="button" className="btn-primary text-sm h-10" disabled={memberBusy || !memberUserId} onClick={() => void onAddMember()}>
              {t('app.admin.org.add', { defaultValue: 'Add' })}
            </button>
          </div>
          <ul className="text-sm space-y-1">
            {(members[memberUnitId] || []).map((m) => (
              <li key={m.user_id} className="flex justify-between gap-2 border-b border-slate-100 py-1">
                <span>{m.full_name || m.email}</span>
                <button
                  type="button"
                  className="btn text-xs text-rose-700 hover:underline"
                  disabled={memberBusy}
                  onClick={() => void onRemoveMember(memberUnitId, m.user_id)}
                >
                  {t('app.admin.org.remove', { defaultValue: 'Remove' })}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  )
}
