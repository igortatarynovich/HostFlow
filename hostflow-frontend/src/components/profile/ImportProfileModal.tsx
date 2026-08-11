import { memo, useState, useRef } from 'react'
import { Modal } from '../Modal'
import ErrorRecoveryBanner from '../ErrorRecoveryBanner'
import { useI18n } from '../../i18n'

interface ImportProfileModalProps {
  onClose: () => void
  onImport: (file: File) => Promise<void>
}

function ImportProfileModal({ onClose, onImport }: ImportProfileModalProps) {
  const { t } = useI18n()
  const [file, setFile] = useState<File | null>(null)
  const [fileName, setFileName] = useState<string>('')
  const [importing, setImporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0]
    if (selectedFile) {
      // Ensure JSON file
      if (!selectedFile.name.endsWith('.json')) {
        setError(t('app.settings.candidate_profiles.import.errors.invalid_format', { defaultValue: 'Invalid file format. Select a JSON file (.json)' }))
        setFile(null)
        setFileName('')
        return
      }
      setFile(selectedFile)
      setFileName(selectedFile.name)
      setError(null)
    }
  }

  const handleImport = async () => {
    if (!file) {
      setError(t('app.settings.candidate_profiles.import.errors.select_file', { defaultValue: 'Select a file to import' }))
      return
    }

    setImporting(true)
    setError(null)
    try {
      await onImport(file)
    } catch (err: any) {
      setError(err?.message || t('app.settings.candidate_profiles.import.errors.import_failed', { defaultValue: 'Failed to import profile' }))
    } finally {
      setImporting(false)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()

    const droppedFile = e.dataTransfer.files[0]
    if (droppedFile) {
      if (!droppedFile.name.endsWith('.json')) {
        setError(t('app.settings.candidate_profiles.import.errors.invalid_format', { defaultValue: 'Invalid file format. Select a JSON file (.json)' }))
        setFile(null)
        setFileName('')
        return
      }
      setFile(droppedFile)
      setFileName(droppedFile.name)
      setError(null)
    }
  }

  return (
    <Modal open={true} onClose={onClose} title={t('app.settings.candidate_profiles.import.title', { defaultValue: 'Import profile' })}>
      <div className="space-y-4">
        <div className="text-sm text-slate-600">
          {t('app.settings.candidate_profiles.import.description', {
            defaultValue:
              'Select a JSON file with profile configuration for import. The file must contain a profile structure exported from the system.',
          })}
        </div>

        {/* Drag and drop zone */}
        <div
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors ${
            file
              ? 'border-green-300 bg-green-50'
              : 'border-slate-300 bg-slate-50 hover:border-blue-300 hover:bg-blue-50'
          }`}
          onClick={() => fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".json,application/json"
            onChange={handleFileSelect}
            className="hidden"
            disabled={importing}
          />
          {file ? (
            <>
              <svg
                className="mb-2 h-12 w-12 text-green-600"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              <div className="text-sm font-medium text-slate-900">{fileName}</div>
              <div className="mt-1 text-xs text-slate-500">
                {t('app.settings.candidate_profiles.import.select_other', { defaultValue: 'Click to select another file' })}
              </div>
            </>
          ) : (
            <>
              <svg
                className="mb-2 h-12 w-12 text-slate-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
              </svg>
              <div className="text-sm font-medium text-slate-700">
                {t('app.settings.candidate_profiles.import.dropzone', { defaultValue: 'Drop file here or click to select' })}
              </div>
              <div className="mt-1 text-xs text-slate-500">
                {t('app.settings.candidate_profiles.import.json_only', { defaultValue: 'JSON files only (.json)' })}
              </div>
            </>
          )}
        </div>

        {error && (
          <ErrorRecoveryBanner
            info={{ title: error, hint: t('app.settings.candidate_profiles.import.errors.hint', { defaultValue: 'Fix the file or retry the action.' }) }}
            compact
          />
        )}

        <div className="rounded border border-blue-200 bg-blue-50 p-3 text-xs text-blue-700">
          <div className="font-semibold mb-1">{t('app.settings.candidate_profiles.import.important_title', { defaultValue: 'Important:' })}</div>
          <ul className="list-disc list-inside space-y-1">
            <li>
              {t('app.settings.candidate_profiles.import.duplicate_suffix_hint', {
                defaultValue:
                  'If a profile with this code already exists, a new profile will be created with the "_imported" suffix',
              })}
            </li>
            <li>
              {t('app.settings.candidate_profiles.import.copy_fields_hint', {
                defaultValue: 'All fields, stages and documents from the imported profile will be copied',
              })}
            </li>
            <li>
              {t('app.settings.candidate_profiles.import.new_profile_hint', {
                defaultValue: 'The imported profile will be created as new and will not be linked to the original',
              })}
            </li>
          </ul>
        </div>

        <div className="flex gap-2 justify-end border-t border-slate-200 pt-4">
          <button
            type="button"
            onClick={onClose}
            disabled={importing}
            className="btn-secondary"
          >
            {t('common.actions.cancel', { defaultValue: 'Cancel' })}
          </button>
          <button
            type="button"
            onClick={handleImport}
            disabled={!file || importing}
            className="btn-primary"
          >
            {importing
              ? t('app.settings.candidate_profiles.import.actions.importing', { defaultValue: 'Importing...' })
              : t('app.settings.candidate_profiles.import.actions.import', { defaultValue: 'Import' })}
          </button>
        </div>
      </div>
    </Modal>
  )
}

export default memo(ImportProfileModal)
