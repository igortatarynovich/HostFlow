import { useCallback, useEffect, useMemo, useState } from 'react'
import clsx from 'clsx'
import { IconChevronLeft, IconChevronRight } from '@tabler/icons-react'
import type { CommunicationThread } from '../../api/communications'
import { useI18n } from '../../i18n'
import { emailCustomFolderNameOf, emailThreadInFolder, type EmailFolderKey } from '../../utils/emailInboxFolders'

const LS_KEY = 'hf:email-workspace:v2'
const SESSION_FOLDERS_COLLAPSED_KEY = 'hf:email:foldersCollapsed'

function readSaved(): Record<string, any> {
  try {
    const raw = window.localStorage.getItem(LS_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

type Props = {
  threads: CommunicationThread[]
  activeFolder: EmailFolderKey
  onFolderChange: (folder: EmailFolderKey) => void
}

export default function InboxEmailFolderRail({ threads, activeFolder, onFolderChange }: Props) {
  const { t } = useI18n()
  const [foldersCollapsed, setFoldersCollapsed] = useState(() => {
    try {
      return sessionStorage.getItem(SESSION_FOLDERS_COLLAPSED_KEY) === '1'
    } catch {
      return false
    }
  })
  const [showMoreFolders, setShowMoreFolders] = useState(false)
  const [newFolderName, setNewFolderName] = useState('')
  const [customFolders, setCustomFolders] = useState<string[]>(() => {
    const s = readSaved().customFolders
    return Array.isArray(s) ? s : []
  })

  useEffect(() => {
    try {
      sessionStorage.setItem(SESSION_FOLDERS_COLLAPSED_KEY, foldersCollapsed ? '1' : '0')
    } catch {
      /* ignore */
    }
  }, [foldersCollapsed])

  const allCustomFolders = useMemo(() => {
    const fromThreads = threads.map((th) => emailCustomFolderNameOf(th)).filter(Boolean) as string[]
    return Array.from(new Set([...customFolders, ...fromThreads])).sort((a, b) => a.localeCompare(b))
  }, [customFolders, threads])

  const folderLabel = useCallback(
    (key: EmailFolderKey): string => {
      if (key.startsWith('custom:')) return key.slice('custom:'.length)
      switch (key) {
        case 'inbox':
          return t('app.communications.email.folders.inbox', { defaultValue: 'Inbox' })
        case 'unread':
          return t('app.communications.email.folders.unread', { defaultValue: 'Unread' })
        case 'archive':
          return t('app.communications.email.folders.archive', { defaultValue: 'Archive' })
        case 'sent':
          return t('app.communications.email.folders.sent', { defaultValue: 'Sent' })
        case 'trash':
          return t('app.communications.email.folders.deleted', { defaultValue: 'Deleted' })
        case 'all':
          return t('app.communications.email.folders.all', { defaultValue: 'All' })
        case 'assigned':
          return t('app.communications.email.folders.assigned', { defaultValue: 'Assigned' })
        case 'unlinked':
          return t('app.communications_messages.dialogs.link_filter_unlinked')
        default:
          return String(key)
      }
    },
    [t],
  )

  const folderCount = useCallback(
    (key: EmailFolderKey) => threads.filter((x) => emailThreadInFolder(x, key)).length,
    [threads],
  )

  const inboxUnreadBadge = useMemo(
    () => threads.filter((th) => emailThreadInFolder(th, 'inbox') && Number(th.unread_count || 0) > 0).length,
    [threads],
  )

  const primaryFolderItems = useMemo(
    () =>
      (['inbox', 'unread', 'archive'] as const).map((key) => ({
        key: key as EmailFolderKey,
        label: folderLabel(key),
        count: key === 'inbox' ? inboxUnreadBadge : folderCount(key),
      })),
    [folderCount, folderLabel, inboxUnreadBadge],
  )

  const moreSystemFolderItems = useMemo(
    () =>
      (['sent', 'trash', 'all'] as const).map((key) => ({
        key: key as EmailFolderKey,
        label: folderLabel(key),
        count: folderCount(key),
      })),
    [folderCount, folderLabel],
  )

  const customFolderItems = useMemo(
    () =>
      allCustomFolders.map((name) => {
        const key = `custom:${name}` as EmailFolderKey
        return { key, label: name, count: folderCount(key) }
      }),
    [allCustomFolders, folderCount],
  )

  const createFolder = () => {
    const name = newFolderName.trim()
    if (!name) return
    if (!customFolders.includes(name)) setCustomFolders((prev) => [...prev, name])
    setNewFolderName('')
    onFolderChange(`custom:${name}`)
  }

  useEffect(() => {
    try {
      const prev = readSaved()
      window.localStorage.setItem(LS_KEY, JSON.stringify({ ...prev, customFolders }))
    } catch {
      /* ignore */
    }
  }, [customFolders])

  return (
    <aside
      className={clsx(
        'rounded-lg border border-slate-200 bg-white',
        foldersCollapsed && 'flex flex-col items-center p-1',
        !foldersCollapsed && 'p-4',
      )}
    >
      {foldersCollapsed ? (
        <button
          type="button"
          className="rounded-md p-2 text-slate-600 transition hover:bg-slate-100"
          title={t('app.communications.email.folders.expand', { defaultValue: 'Show folders' })}
          aria-label={t('app.communications.email.folders.expand', { defaultValue: 'Show folders' })}
          onClick={() => setFoldersCollapsed(false)}
        >
          <IconChevronRight size={20} stroke={1.75} />
        </button>
      ) : (
        <>
          <div className="mb-2 flex items-center justify-between gap-2">
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              {t('app.communications.email.labels.folders', { defaultValue: 'Folders' })}
            </div>
            <button
              type="button"
              className="rounded-md p-1 text-slate-500 transition hover:bg-slate-100"
              title={t('app.communications.email.folders.collapse', { defaultValue: 'Collapse folders' })}
              aria-label={t('app.communications.email.folders.collapse', { defaultValue: 'Collapse folders' })}
              onClick={() => setFoldersCollapsed(true)}
            >
              <IconChevronLeft size={18} stroke={1.75} />
            </button>
          </div>
          <div className="space-y-1">
            {primaryFolderItems.map((item) => (
              <button
                key={item.key}
                type="button"
                onClick={() => onFolderChange(item.key)}
                className={clsx(
                  'btn-secondary w-full justify-between',
                  activeFolder === item.key && 'border-brand-600 bg-brand-50 text-brand-800',
                )}
              >
                <span className="truncate">{item.label}</span>
                <span className="badge ml-2 bg-slate-100 text-slate-600">{item.count}</span>
              </button>
            ))}
          </div>
          <button type="button" className="btn-secondary btn-xs mt-2 w-full" onClick={() => setShowMoreFolders((v) => !v)}>
            {showMoreFolders
              ? t('app.communications.email.folders.more_hide', { defaultValue: 'Hide extra folders' })
              : t('app.communications.email.folders.more_show', { defaultValue: 'More folders' })}
          </button>
          {showMoreFolders && (
            <div className="mt-2 space-y-1 border-t border-slate-100 pt-2">
              {[...moreSystemFolderItems, ...customFolderItems].map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => onFolderChange(item.key)}
                  className={clsx(
                    'btn-secondary w-full justify-between',
                    activeFolder === item.key && 'border-brand-600 bg-brand-50 text-brand-800',
                  )}
                >
                  <span className="truncate">{item.label}</span>
                  <span className="badge ml-2 bg-slate-100 text-slate-600">{item.count}</span>
                </button>
              ))}
            </div>
          )}
          <div className="mt-3 border-t border-slate-100 pt-3">
            <div className="mb-1 text-xs text-slate-500">{t('app.communications.email.labels.new_folder', { defaultValue: 'New folder' })}</div>
            <div className="flex gap-2">
              <input value={newFolderName} onChange={(e) => setNewFolderName(e.target.value)} className="input text-xs" />
              <button type="button" onClick={createFolder} className="btn-secondary btn-sm shrink-0">
                {t('common.actions.add', { defaultValue: 'Add' })}
              </button>
            </div>
          </div>
        </>
      )}
    </aside>
  )
}
