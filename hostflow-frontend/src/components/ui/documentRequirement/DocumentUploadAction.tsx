import { useRef } from 'react'
import { Button } from '../Button'

export function DocumentUploadAction({
  label,
  disabled,
  onFile,
  appearance = 'button',
  inputId,
}: {
  label: string
  disabled?: boolean
  onFile: (file: File) => void
  appearance?: 'button' | 'link' | 'hidden'
  /** Lets another control open this picker, for example an overflow menu. */
  inputId?: string
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const open = () => inputRef.current?.click()
  return (
    <>
      {appearance === 'hidden' ? null : appearance === 'link' ? (
        <Button type="button" variant="link" disabled={disabled} onClick={open}>
          {label}
        </Button>
      ) : (
        <Button type="button" variant="primary" size="compact" disabled={disabled} onClick={open}>
          {label}
        </Button>
      )}
      <input
        ref={inputRef}
        id={inputId}
        type="file"
        className="sr-only"
        disabled={disabled}
        onChange={(event) => {
          const file = event.target.files?.[0]
          event.target.value = ''
          if (file) onFile(file)
        }}
      />
    </>
  )
}
