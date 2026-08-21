import type { ComponentType } from 'react'
import { IdentityCapability } from '../capabilities/shell/identity'
import { StatusCapability } from '../capabilities/shell/status'
import { NotesCapability } from '../capabilities/notes/NotesCapability'
import { ConsentCapability } from '../capabilities/consent/ConsentCapability'
import { CommunicationCapability } from '../capabilities/communication/CommunicationCapability'
import { FormsCapability } from '../capabilities/forms/FormsCapability'
import { RecruitmentStageContribution } from '../../modules/recruitment/contributions/stage'
import { RecruitmentVacancyContribution } from '../../modules/recruitment/contributions/vacancy'
import { RecruitmentAssigneeContribution } from '../../modules/recruitment/contributions/assignee'
import { OptionalAddonFixture } from './fixtures/optional-addon'
import type { WorkspaceRendererComponentId } from './registry'
import type { WorkspaceCapabilityRenderContext } from './renderContext'

export type WorkspaceCapabilityRenderer = ComponentType<WorkspaceCapabilityRenderContext>

/**
 * Runtime bind of registry `component_id` → renderer.
 * Registry stays technical (paths only). This map is the actual import.
 */
export const WORKSPACE_CAPABILITY_RENDERERS = {
  'workspace.shell.identity': IdentityCapability,
  'workspace.shell.status': StatusCapability,
  'workspace.shared.notes': NotesCapability,
  'workspace.shared.consent': ConsentCapability,
  'workspace.surface.communication': CommunicationCapability,
  'workspace.surface.forms': FormsCapability,
  'workspace.module.recruitment.stage': RecruitmentStageContribution,
  'workspace.module.recruitment.vacancy': RecruitmentVacancyContribution,
  'workspace.module.recruitment.assignee': RecruitmentAssigneeContribution,
  'workspace.fixture.optional_addon': OptionalAddonFixture,
} as const satisfies Partial<Record<WorkspaceRendererComponentId, WorkspaceCapabilityRenderer>>
