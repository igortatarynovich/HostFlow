// замените строку импорта на type-only
import { useEffect, type PropsWithChildren } from 'react'

export function Modal({ open, onClose, title, children }:{
  open: boolean
  onClose: ()=>void
  title?: string
} & PropsWithChildren){
  useEffect(() => {
    function onKey(e: KeyboardEvent){ if (e.key === 'Escape') onClose() }
    if (open) window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50">
      <div className="absolute inset-0 bg-black/40" onClick={onClose}/>
      <div className="absolute inset-0 grid place-items-center p-2 sm:p-4">
        <div className="card modal-surface w-full max-w-lg max-h-[calc(100vh-1rem)] overflow-y-auto p-4 sm:max-h-[calc(100vh-2rem)] sm:p-5">
          {title && <h3 className="text-lg font-semibold mb-4">{title}</h3>}
          {children}
        </div>
      </div>
    </div>
  )
}
