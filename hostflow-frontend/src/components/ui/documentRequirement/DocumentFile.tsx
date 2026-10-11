export function DocumentFile({ name }: { name: string }) {
  if (!name) return null
  return <span className="min-w-0 truncate text-sm text-slate-900">{name}</span>
}
