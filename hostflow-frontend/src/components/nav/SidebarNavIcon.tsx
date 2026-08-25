import { HostflowUiIcon } from '../../platform/icons/HostflowUiIcon'
import { PlatformIcon } from '../../platform/icons/PlatformIcon'
import type { VisualAssetSizeToken } from '../../platform/icons/visualAssets.generated'
import { SIDEBAR_DEFAULT_ICON, SIDEBAR_ITEM_ICON, type SidebarIconSpec } from '../../nav/sidebarIconMap'

type SidebarNavIconProps = {
  itemKey: string
  size?: VisualAssetSizeToken | number
}

function renderSpec(spec: SidebarIconSpec, size: VisualAssetSizeToken | number) {
  if (spec.kind === 'platform') {
    return (
      <PlatformIcon
        id={spec.id}
        size={size}
        variant={spec.variant ?? 'default'}
        theme="light"
        className="brightness-0 invert"
      />
    )
  }
  return <HostflowUiIcon id={spec.id} size={size} theme="light" tone="onPrimary" />
}

/** Sidebar nav glyph on brand-900 rail (white stroke via tone onPrimary). */
export function SidebarNavIcon({ itemKey, size = 16 }: SidebarNavIconProps) {
  const spec = SIDEBAR_ITEM_ICON[itemKey] ?? SIDEBAR_DEFAULT_ICON
  return renderSpec(spec, size)
}
