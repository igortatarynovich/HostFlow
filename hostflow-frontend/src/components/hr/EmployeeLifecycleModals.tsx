import { useEffect, useState } from 'react'
import { endHrEmployeeRecordEmployment, returnWorkforceHrReviewToRecruitment } from '../../api/workforce'
import { Modal } from '../Modal'
import { Button } from '../ui/Button'

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

export function EndEmploymentModal({
  employeeId,
  open,
  onClose,
  onCompleted,
}: {
  employeeId: string
  open: boolean
  onClose: () => void
  onCompleted: () => Promise<unknown> | unknown
}) {
  const [endedOn, setEndedOn] = useState(todayIso)
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setEndedOn(todayIso())
    setReason('')
    setError(null)
  }, [open])

  const submit = async () => {
    if (!endedOn || reason.trim().length < 3) {
      setError('Podaj datę zakończenia i powód.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      const result = await endHrEmployeeRecordEmployment(employeeId, { ended_on: endedOn, reason: reason.trim() })
      if (!result.accepted) {
        setError(result.reason || 'Nie udało się zakończyć zatrudnienia.')
        return
      }
      await onCompleted()
      onClose()
    } catch {
      setError('Nie udało się zakończyć zatrudnienia.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Zakończ zatrudnienie">
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          Zakończenie zamknie bieżące Employment. Karta osoby i historia pozostaną dostępne.
        </p>
        <label className="block text-sm font-medium text-slate-800">
          Data zakończenia
          <input className="input mt-1 w-full" type="date" value={endedOn} onChange={(event) => setEndedOn(event.target.value)} />
        </label>
        <label className="block text-sm font-medium text-slate-800">
          Powód
          <textarea
            className="input mt-1 min-h-24 w-full resize-y"
            value={reason}
            maxLength={1000}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Powód zakończenia zatrudnienia"
          />
        </label>
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
          <p className="font-medium text-slate-900">Działania systemowe</p>
          <ul className="mt-2 list-disc space-y-1 pl-5">
            <li>Employment otrzyma stan zakończony i datę końcową.</li>
            <li>Powód zostanie zapisany w historii lifecycle.</li>
            <li>Formalności końcowe, w tym wyrejestrowanie ZUS, pozostaną widoczne jako działania operacyjne.</li>
          </ul>
        </div>
        {error ? <p className="alert-error text-sm">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button onClick={onClose} disabled={saving}>Anuluj</Button>
          <Button variant="danger" onClick={() => void submit()} disabled={saving}>
            {saving ? 'Zapisywanie…' : 'Zakończ zatrudnienie'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export function ReturnToRecruitmentModal({
  employeeId,
  open,
  onClose,
  onCompleted,
}: {
  employeeId: string
  open: boolean
  onClose: () => void
  onCompleted: () => Promise<unknown> | unknown
}) {
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setReason('')
    setError(null)
  }, [open])

  const submit = async () => {
    if (reason.trim().length < 3) {
      setError('Podaj powód zwrotu do Recruitment.')
      return
    }
    setSaving(true)
    setError(null)
    try {
      await returnWorkforceHrReviewToRecruitment(employeeId, reason.trim())
      await onCompleted()
      onClose()
    } catch {
      setError('Nie udało się zwrócić sprawy do Recruitment.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} onClose={onClose} title="Wróć do rekrutacji">
      <div className="space-y-4">
        <p className="text-sm text-slate-600">Proces HR zostanie zatrzymany do czasu kolejnego przekazania z Recruitment.</p>
        <label className="block text-sm font-medium text-slate-800">
          Powód
          <textarea
            className="input mt-1 min-h-24 w-full resize-y"
            value={reason}
            maxLength={1000}
            onChange={(event) => setReason(event.target.value)}
          />
        </label>
        {error ? <p className="alert-error text-sm">{error}</p> : null}
        <div className="flex justify-end gap-2">
          <Button onClick={onClose} disabled={saving}>Anuluj</Button>
          <Button variant="primary" onClick={() => void submit()} disabled={saving}>
            {saving ? 'Zapisywanie…' : 'Wróć do rekrutacji'}
          </Button>
        </div>
      </div>
    </Modal>
  )
}
