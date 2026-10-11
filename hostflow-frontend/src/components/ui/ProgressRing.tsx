export function ProgressRing({
  value,
  max,
  size = 32,
}: {
  value: number
  max: number
  size?: number
}) {
  const safeMax = max > 0 ? max : 0
  const ratio = safeMax > 0 ? Math.max(0, Math.min(1, value / safeMax)) : 0
  const radius = 12
  const circumference = 2 * Math.PI * radius
  const complete = safeMax > 0 && value >= safeMax
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden className="shrink-0">
      <circle cx="16" cy="16" r={radius} fill="none" stroke="currentColor" strokeWidth="3" className="text-slate-200" />
      <circle
        cx="16"
        cy="16"
        r={radius}
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
        strokeDasharray={`${circumference * ratio} ${circumference}`}
        transform="rotate(-90 16 16)"
        className={complete ? 'text-emerald-500' : 'text-brand-600'}
      />
    </svg>
  )
}
