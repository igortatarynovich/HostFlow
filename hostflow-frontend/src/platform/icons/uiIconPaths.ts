export {
  isUiIconId,
  resolveUiIconKey,
  resolveUiIconUrl,
  UI_ICON_ALIASES,
  UI_ICON_KEYS,
  UI_ICONS,
  type UiIconAliasId,
  type UiIconId,
  type UiIconKey,
  type UiIconRecord,
  type UiIconSection,
  type UiIconTheme,
} from './uiIconPaths.generated'

import type { UiIconId } from './uiIconPaths.generated'

/** Detail Rail contact channel → Figma UI icon id. */
export const DETAIL_RAIL_CONTACT_UI_ICON: Record<'phone' | 'whatsapp' | 'email', UiIconId> = {
  phone: 'позвонить',
  whatsapp: 'whatsapp',
  email: 'email',
}
