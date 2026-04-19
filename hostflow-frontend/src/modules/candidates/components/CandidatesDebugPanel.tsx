// src/modules/candidates/components/CandidatesDebugPanel.tsx
//
// Debug overlay shown only when the Candidates page is opened with `?debug=1`.
// Renders:
//   * a "client view" diagnostic that hits two debug-only backend endpoints
//     (`candidates/debug-client-view` + `candidates/debug-client-view/force-two`),
//   * five hit-test traces (mousedown / click / mouseup / click-bubble /
//     mouseup-bubble) used when reproducing pointer-event regressions on
//     the candidates table,
//   * a snapshot of the work-panel preview state.
//
// Extracted from `src/pages/Candidates.tsx` as part of the Phase 1 #4 god-
// component split (5731 → smaller chunks). Pure presentational + a small
// async handler delegated back to the page via `onForceTwo`.

import { useState } from 'react'

import api from '../../../api/client'
import type { TranslateFn } from '../../../i18n'

export interface DebugHit {
  tag?: string
  className?: string
  pointerEvents?: string
  insideTable?: boolean
}

export interface CandidatesDebugPanelProps {
  t: TranslateFn
  /** Reload the candidates list after a destructive debug action. */
  onForceTwoApplied: () => void
  // Pointer-event traces collected by the page-level listeners.
  debugHit: DebugHit | null
  debugClickHit: DebugHit | null
  debugMouseUpHit: DebugHit | null
  debugClickHitBubble: DebugHit | null
  debugMouseUpHitBubble: DebugHit | null
  // Preview state snapshot (visualised inside the debug panel).
  sidebarOpen: boolean
  selectedCandidateId: string | null
}

export function CandidatesDebugPanel({
  t,
  onForceTwoApplied,
  debugHit,
  debugClickHit,
  debugMouseUpHit,
  debugClickHitBubble,
  debugMouseUpHitBubble,
  sidebarOpen,
  selectedCandidateId,
}: CandidatesDebugPanelProps) {
  const [debugClientView, setDebugClientView] = useState<Record<string, unknown> | null>(null)
  const [debugClientViewLoading, setDebugClientViewLoading] = useState(false)
  const [debugClientViewError, setDebugClientViewError] = useState<string | null>(null)

  const handleProbe = async () => {
    setDebugClientViewError(null)
    setDebugClientViewLoading(true)
    try {
      const { data } = await api.get<Record<string, unknown>>('candidates/debug-client-view')
      setDebugClientView(data)
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      setDebugClientViewError(
        err?.response?.data?.detail ?? err?.message ?? t('common.errors.request_failed', { defaultValue: 'Request failed' }),
      )
      setDebugClientView(null)
    } finally {
      setDebugClientViewLoading(false)
    }
  }

  const handleForceTwo = async () => {
    setDebugClientViewError(null)
    setDebugClientViewLoading(true)
    try {
      const { data } = await api.post<{ updated?: number; message?: string }>(
        'candidates/debug-client-view/force-two',
      )
      setDebugClientView(data as Record<string, unknown>)
      onForceTwoApplied()
    } catch (e: unknown) {
      const err = e as { response?: { data?: { detail?: string } }; message?: string }
      setDebugClientViewError(
        err?.response?.data?.detail ?? err?.message ?? t('common.errors.request_failed', { defaultValue: 'Request failed' }),
      )
      setDebugClientView(null)
    } finally {
      setDebugClientViewLoading(false)
    }
  }

  return (
    <div className="mx-4 mt-2 mb-2 p-3 rounded-lg border border-amber-200 bg-amber-50 text-sm">
      <div className="font-medium text-amber-900 mb-2">
        {t('app.candidates.debug.client_view', { defaultValue: 'Debug: client view' })}
      </div>
      <div className="flex flex-wrap items-center gap-2 mb-2">
        <button
          type="button"
          className="px-3 py-1.5 rounded border border-amber-400 bg-white hover:bg-amber-100 text-amber-900 disabled:opacity-50"
          disabled={debugClientViewLoading}
          onClick={handleProbe}
        >
          {debugClientViewLoading ? '…' : 'Проверить handoffs'}
        </button>
        <button
          type="button"
          className="px-3 py-1.5 rounded border border-amber-600 bg-amber-500 hover:bg-amber-600 text-white disabled:opacity-50"
          disabled={debugClientViewLoading}
          onClick={handleForceTwo}
        >
          Оставить 2 handoff и обновить список
        </button>
      </div>
      {debugClientViewError && <div className="text-red-600 mb-1">{debugClientViewError}</div>}
      {debugClientView && (
        <pre className="text-xs bg-white p-2 rounded border overflow-auto max-h-32">
          {JSON.stringify(debugClientView, null, 2)}
        </pre>
      )}

      <HitTrace
        hit={debugHit}
        title={t('app.candidates.debug.mousedown_hit', { defaultValue: 'Debug: mousedown hit' })}
        tone="amber"
      />
      <HitTrace
        hit={debugClickHit}
        title={t('app.candidates.debug.click_after_mousedown', { defaultValue: 'Debug: click AFTER mousedown' })}
        tone="indigo"
      />

      <div className="mt-2 p-2 rounded border border-slate-200 bg-white/60">
        <div className="text-xs font-semibold text-slate-900 mb-1">
          {t('app.candidates.debug.current_preview_state', { defaultValue: 'Debug: current preview state' })}
        </div>
        <div className="text-[11px] text-slate-900">
          <div>
            sidebarOpen: <span className="font-mono">{String(sidebarOpen)}</span>
          </div>
          <div>
            selectedCandidateId: <span className="font-mono">{selectedCandidateId ?? 'null'}</span>
          </div>
        </div>
      </div>

      <HitTrace
        hit={debugMouseUpHit}
        title={t('app.candidates.debug.mouseup_hit', { defaultValue: 'Debug: mouseup hit' })}
        tone="cyan"
      />
      <HitTrace
        hit={debugClickHitBubble}
        title={t('app.candidates.debug.click_hit_bubble', { defaultValue: 'Debug: click hit (bubble)' })}
        tone="violet"
        showClassName={false}
      />
      <HitTrace
        hit={debugMouseUpHitBubble}
        title={t('app.candidates.debug.mouseup_hit_bubble', { defaultValue: 'Debug: mouseup hit (bubble)' })}
        tone="sky"
        showClassName={false}
      />
    </div>
  )
}

// ---------------------------------------------------------------------------
// HitTrace — collapsible diagnostic block reused by the 5 debug hit panels.
// ---------------------------------------------------------------------------

type ToneToken = 'amber' | 'indigo' | 'cyan' | 'violet' | 'sky'

const TONE_CLASSES: Record<ToneToken, { container: string; title: string; body: string }> = {
  amber: {
    container: 'mt-2 p-2 rounded border border-amber-200 bg-amber-100/50',
    title: 'text-xs font-semibold text-amber-900 mb-1',
    body: 'text-[11px] text-amber-900',
  },
  indigo: {
    container: 'mt-2 p-2 rounded border border-indigo-200 bg-indigo-100/40',
    title: 'text-xs font-semibold text-indigo-900 mb-1',
    body: 'text-[11px] text-indigo-900',
  },
  cyan: {
    container: 'mt-2 p-2 rounded border border-cyan-200 bg-cyan-100/30',
    title: 'text-xs font-semibold text-cyan-900 mb-1',
    body: 'text-[11px] text-cyan-900',
  },
  violet: {
    container: 'mt-2 p-2 rounded border border-violet-200 bg-violet-100/30',
    title: 'text-xs font-semibold text-violet-900 mb-1',
    body: 'text-[11px] text-violet-900',
  },
  sky: {
    container: 'mt-2 p-2 rounded border border-sky-200 bg-sky-100/20',
    title: 'text-xs font-semibold text-sky-900 mb-1',
    body: 'text-[11px] text-sky-900',
  },
}

function HitTrace({
  hit,
  title,
  tone,
  showClassName = true,
}: {
  hit: DebugHit | null
  title: string
  tone: ToneToken
  showClassName?: boolean
}) {
  if (!hit) return null
  const cls = TONE_CLASSES[tone]
  return (
    <div className={cls.container}>
      <div className={cls.title}>{title}</div>
      <div className={cls.body}>
        <div>
          tag: <span className="font-mono">{hit.tag ?? '—'}</span>
        </div>
        <div>
          pointer-events: <span className="font-mono">{hit.pointerEvents ?? '—'}</span>
        </div>
        <div>
          insideTable: <span className="font-mono">{String(Boolean(hit.insideTable))}</span>
        </div>
        {showClassName && hit.className ? (
          <div className="mt-1">
            class: <span className="font-mono">{hit.className}</span>
          </div>
        ) : null}
      </div>
    </div>
  )
}
