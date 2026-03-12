type Props = {
  cols?: 1 | 2 | 3
  children: React.ReactNode
}

export function FieldGrid({ cols = 2, children }: Props) {
  if (cols === 1) return <div className="space-y-3">{children}</div>
  if (cols === 3) return <div className="grid grid-cols-1 gap-4 md:grid-cols-3">{children}</div>
  return <div className="grid grid-cols-1 gap-4 md:grid-cols-2">{children}</div>
}
