/**
 * PMI-UI — platform design-system public surface.
 *
 * Module compositions import primitives from here (or from locked Layer-2 paths
 * re-exported below). Do not invent a second kit.
 *
 * Authority: scripts/architecture/ui_primitive_authority.json
 * Spec: docs/specs/frontend/PRIMITIVES_V1.md
 */

export { Button } from '../../components/ui/Button'
export { Checkbox } from '../../components/ui/Checkbox'
export { Chip } from '../../components/ui/Chip'
export { Combobox } from '../../components/ui/Combobox'
export { MultiCombobox } from '../../components/ui/MultiCombobox'
export { FieldGrid } from '../../components/ui/FieldGrid'
export { SectionCard } from '../../components/ui/SectionCard'
export { StatusBadge } from '../../components/ui/StatusBadge'
export {
  STATUS_BADGE_SEMANTIC_CLASSES,
  STATUS_BADGE_SEMANTIC_CLASSES_INVERSE,
  nextActionPriorityToSemantic,
  stageSemanticForCode,
} from '../../components/ui/statusBadgeSemantics'

export { PageShell, PageShellHeader, PageShellBody } from '../../components/layout/PageShell'
export { Toolbar } from '../../components/layout/Toolbar'
export { Modal } from '../../components/Modal'
export { default as EmptyStatePanel } from '../../components/EmptyStatePanel'
export { ToastProvider, useToast } from '../../components/Toast'

/** Action display over backend NextActionDTO — not a domain decision engine. */
export { NextActionBadge } from './NextActionBadge'
export { default as NextActionBadgeDefault } from './NextActionBadge'
