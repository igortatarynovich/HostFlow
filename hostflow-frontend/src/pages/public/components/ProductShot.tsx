type ProductShotProps = {
  src: string
  caption: string
  badge?: string
  /** Larger frame for marketing pages — keeps UI text readable. */
  size?: 'default' | 'hero' | 'feature'
}

/** Product screenshot with caption — for company / landing marketing pages. */
export function ProductShot({ src, caption, badge, size = 'default' }: ProductShotProps) {
  const frame =
    size === 'hero'
      ? 'min-h-[280px] sm:min-h-[360px] lg:min-h-[480px]'
      : size === 'feature'
        ? 'min-h-[220px] sm:min-h-[280px] lg:min-h-[340px]'
        : 'aspect-[16/10]'

  return (
    <figure className="overflow-hidden rounded-2xl border border-slate-200/90 bg-white shadow-[0_20px_50px_-28px_rgba(15,23,42,0.35)]">
      <div className={`relative bg-slate-100 ${frame}`}>
        <img
          src={src}
          alt={caption}
          className="absolute inset-0 h-full w-full object-contain object-top p-1 sm:p-2"
          loading={size === 'hero' ? 'eager' : 'lazy'}
          decoding="async"
        />
      </div>
      {(badge || caption) && (
        <figcaption className="flex flex-wrap items-center gap-2 border-t border-slate-100 px-4 py-3 text-xs leading-snug text-slate-600 sm:text-sm">
          {badge ? (
            <span className="shrink-0 rounded-md bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
              {badge}
            </span>
          ) : null}
          <span>{caption}</span>
        </figcaption>
      )}
    </figure>
  )
}
