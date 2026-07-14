import { useState, useEffect, useRef, useCallback } from 'react'
import { createPortal } from 'react-dom'
import type { ReactNode } from 'react'
import { IconFilter } from '@tabler/icons-react'
import type { Icon as TablerIcon } from '@tabler/icons-react'
import { useI18n } from '../../../i18n'

type TriggerIcon = TablerIcon

type ColumnFilterMenuProps =
  | {
      title: string
      options: Array<{ value: string; label: string }>
      selected: string[]
      onChange: (next: string[]) => void
      count?: number
      /** Override the default funnel icon (used to disambiguate two filters in one header). */
      icon?: TriggerIcon
      children?: undefined
    }
  | {
      title: string
      count?: number
      icon?: TriggerIcon
      children: (close: () => void) => ReactNode
      options?: undefined
      selected?: undefined
      onChange?: undefined
    }

export function ColumnFilterMenu(props: ColumnFilterMenuProps) {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const buttonRef = useRef<HTMLButtonElement | null>(null)
  const menuRef = useRef<HTMLDivElement | null>(null)
  const [menuPosition, setMenuPosition] = useState<{ top: number; left: number } | null>(null)
  // Локальное состояние для выбранных значений (применяется только при закрытии)
  const [localSelected, setLocalSelected] = useState<string[]>(props.selected || [])

  // Синхронизируем локальное состояние с props при открытии меню
  useEffect(() => {
    if (open && props.selected) {
      setLocalSelected(props.selected)
    }
  }, [open, props.selected])

  // Вычисляем позицию меню синхронно при открытии
  const calculatePosition = useCallback(() => {
    if (!buttonRef.current) return null
    const buttonRect = buttonRef.current.getBoundingClientRect()
    const menuWidth = 288 // w-72 = 18rem = 288px
    const padding = 8
    let left = buttonRect.right - menuWidth
    if (left < padding) {
      left = padding
    }
    if (left + menuWidth > window.innerWidth - padding) {
      left = window.innerWidth - menuWidth - padding
    }
    return {
      top: buttonRect.bottom + 8,
      left: Math.max(padding, Math.min(left, window.innerWidth - menuWidth - padding)),
    }
  }, [])

  const handleClose = () => {
    // При закрытии применяем изменения только если они изменились
    if (props.onChange) {
      const currentSelected = props.selected || []
      const hasChanged = 
        localSelected.length !== currentSelected.length ||
        localSelected.some(val => !currentSelected.includes(val)) ||
        currentSelected.some(val => !localSelected.includes(val))
      
      if (hasChanged) {
        props.onChange(localSelected)
      }
    }
    setOpen(false)
  }

  // Закрываем меню без применения изменений (если пользователь открыл превью и нам нужно убрать оверлей).
  const forceClose = useCallback(() => {
    setOpen(false)
  }, [])

  useEffect(() => {
    const handler = () => forceClose()
    window.addEventListener('hf:close-column-filter-menus', handler)
    return () => {
      window.removeEventListener('hf:close-column-filter-menus', handler)
    }
  }, [forceClose])

  useEffect(() => {
    if (!open) {
      setMenuPosition(null)
      return
    }
    
    // Вычисляем позицию сразу при открытии синхронно
    const pos = calculatePosition()
    if (pos) {
      setMenuPosition(pos)
    }
    
    // Обновляем позицию при изменении размеров/скролле
    const updatePosition = () => {
      const newPos = calculatePosition()
      if (newPos) {
        setMenuPosition(newPos)
      }
    }

    window.addEventListener('resize', updatePosition)
    window.addEventListener('scroll', updatePosition, true)

    const handler = (event: MouseEvent) => {
      const target = event.target as Node
      if (
        buttonRef.current?.contains(target) ||
        menuRef.current?.contains(target)
      ) {
        return
      }
      handleClose()
    }
    // Используем capture phase для более надежного определения кликов вне меню
    document.addEventListener('mousedown', handler, true)
    
    return () => {
      window.removeEventListener('resize', updatePosition)
      window.removeEventListener('scroll', updatePosition, true)
      document.removeEventListener('mousedown', handler, true)
    }
  }, [open, calculatePosition, handleClose])

  const toggle = (e?: React.MouseEvent) => {
    e?.stopPropagation()
    if (open) {
      handleClose()
    } else {
      setOpen(true)
    }
  }

  const handleReset = () => {
    setLocalSelected([])
    // Применяем сброс сразу
    if (props.onChange) {
      props.onChange([])
    }
    setOpen(false)
  }

  const badgeCount =
    'children' in props && props.children
      ? props.count ?? 0
      : props.selected?.length ?? 0
  const isActive = open || badgeCount > 0

  const menuContent = open && menuPosition && (
    <>
      {/* Без full-screen fixed inset-0: перекрывал всю страницу (в т.ч. таблицу кандидатов) и ломал клики. Закрытие по клику снаружи — document mousedown capture ниже. */}
      <div
        ref={menuRef}
        className="fixed z-[50] w-72 rounded-lg border border-slate-200 bg-white p-3 text-sm shadow-xl"
        style={{
          top: `${menuPosition.top}px`,
          left: `${menuPosition.left}px`,
        }}
        onMouseDown={(e) => e.stopPropagation()}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="text-xs font-semibold uppercase tracking-wide text-slate-400">{props.title}</div>
        {'children' in props && props.children ? (
          <div className="mt-2 space-y-2">{props.children(() => handleClose())}</div>
        ) : props.options && props.options.length > 0 ? (
          <>
            <div className="mt-2 max-h-56 space-y-1 overflow-y-auto pr-1">
              {props.options.map((option) => (
                <label key={option.value} className="flex items-center gap-2 cursor-pointer hover:bg-slate-50 px-1 py-0.5 rounded">
                  <input
                    type="checkbox"
                    checked={localSelected.includes(option.value)}
                    onChange={(event) => {
                      const checked = event.currentTarget.checked
                      setLocalSelected(prev => 
                        checked
                          ? [...prev, option.value]
                          : prev.filter((value) => value !== option.value)
                      )
                    }}
                    onClick={(e) => e.stopPropagation()}
                    className="cursor-pointer"
                  />
                  <span className="flex-1">{option.label}</span>
                </label>
              ))}
            </div>
            <div className="mt-3 flex gap-2 justify-end border-t pt-2">
              <button
                type="button"
                className="btn-secondary btn-xs"
                onClick={handleReset}
                disabled={localSelected.length === 0}
              >
                {t('app.candidates.filters.reset')}
              </button>
              <button
                type="button"
                className="btn-primary btn-xs"
                onClick={handleClose}
              >
                {t('common.actions.apply') || 'Применить'}
              </button>
            </div>
          </>
        ) : (
          <div className="mt-2 text-xs text-slate-500">{t('app.candidates.filters.empty')}</div>
        )}
      </div>
    </>
  )

  return (
    <>
      <div className="relative inline-flex">
        <button
          ref={buttonRef}
          type="button"
          className={`inline-flex h-5 w-5 items-center justify-center rounded leading-none transition-all ${
            isActive
              ? 'opacity-100 text-brand-600 bg-brand-50/70'
              : 'opacity-0 text-slate-400 group-hover:opacity-100 focus-visible:opacity-100 hover:bg-slate-200 hover:text-slate-600'
          }`}
          onClick={toggle}
          onMouseDown={(e) => e.stopPropagation()}
          aria-label={props.title}
          title={props.title}
          aria-pressed={isActive}
        >
          {(() => {
            const TriggerIconComponent = props.icon ?? IconFilter
            return <TriggerIconComponent size={13} className={isActive ? 'text-brand-600' : 'text-slate-500'} />
          })()}
          {badgeCount > 0 && (
            <span className="absolute -right-1.5 -top-1 rounded bg-brand-50 px-1 text-[10px] font-semibold text-brand-700 leading-tight">
              {badgeCount}
            </span>
          )}
        </button>
      </div>
      {typeof document !== 'undefined' && open && menuPosition && createPortal(menuContent, document.body)}
    </>
  )
}
