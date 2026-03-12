import { memo } from 'react'

type ScanHeaderProps = {
  heading: string
  progressPercent: number
}

export const ScanHeader = memo(function ScanHeader({ heading, progressPercent }: ScanHeaderProps) {
  return (
    <div className="mb-4 hidden md:block">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold text-slate-900">{heading}</h1>
        <span className="text-sm font-medium text-slate-600">{progressPercent}%</span>
      </div>
      <div className="h-1.5 w-full rounded-full bg-slate-200 overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-brand-500 to-brand-600 transition-all duration-500 ease-out"
          style={{ width: `${progressPercent}%` }}
        />
      </div>
    </div>
  )
})

