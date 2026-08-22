import type { WorkspaceCapabilityRenderContext } from '../renderContext'

/** Optional/paid contribution fixture — license view only, not a second license SoT. */
export function OptionalAddonFixture(_props: WorkspaceCapabilityRenderContext) {
  return (
    <section className="border border-dashed border-slate-200 p-3 text-sm text-slate-500" data-capability-id="fixture.optional_addon">
      Optional addon (license=optional). Хост размещает; entitlement решает видимость.
    </section>
  )
}
