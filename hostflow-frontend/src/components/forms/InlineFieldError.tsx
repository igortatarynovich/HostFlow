/** Compact inline error under a form control (not a page-level recovery banner). */
export function InlineFieldError({ id, message }: { id?: string; message?: string | null }) {
  if (!message?.trim()) return null
  return (
    <p id={id} className="mt-1 text-xs text-rose-700" role="alert">
      {message}
    </p>
  )
}
