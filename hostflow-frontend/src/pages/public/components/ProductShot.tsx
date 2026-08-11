type ProductShotProps = {
  src: string
  caption: string
  badge?: string
}

/** Product UI mock / screenshot with caption — for company marketing pages. */
export function ProductShot({ src, caption, badge }: ProductShotProps) {
  return (
    <figure className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="relative aspect-[16/10] bg-slate-100">
        <img
          src={src}
          alt={caption}
          className="h-full w-full object-cover object-top"
          loading="lazy"
          decoding="async"
        />
      </div>
      <figcaption className="flex flex-wrap items-center gap-2 border-t border-slate-100 px-4 py-3 text-xs leading-snug text-slate-600">
        {badge ? (
          <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 font-semibold uppercase tracking-wide text-slate-500">
            {badge}
          </span>
        ) : null}
        <span>{caption}</span>
      </figcaption>
    </figure>
  )
}
