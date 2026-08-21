import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { WorkspaceCapabilityRenderContext } from '../../workspace-capability/renderContext'
import { addNote, listNotes, notesSubjectKey } from '../notesOwner'

const get = vi.fn()
const post = vi.fn()

vi.mock('../../../../api/client', () => ({
  api: {
    get: (...args: unknown[]) => get(...args),
    post: (...args: unknown[]) => post(...args),
  },
}))

function ctx(
  patch: Partial<WorkspaceCapabilityRenderContext> = {},
): WorkspaceCapabilityRenderContext {
  return {
    patching: false,
    onClose: () => undefined,
    onRefresh: () => undefined,
    ...patch,
  }
}

describe('notesOwner', () => {
  beforeEach(() => {
    get.mockReset()
    post.mockReset()
  })

  it('pre-convert application has no candidate transport', async () => {
    const subject = ctx({
      application: {
        id: 'app-1',
        module: 'recruitment',
        contact: { name: 'Ada' },
        title: 'Ada',
        status: 'new',
        tab_bucket: 'new',
      },
    })
    expect(notesSubjectKey(subject)).toBe('')
    await expect(listNotes(subject)).resolves.toEqual({ available: false, items: [] })
    expect(get).not.toHaveBeenCalled()
  })

  it('hides candidate notes transport behind the owner', async () => {
    get.mockResolvedValue({ data: [{ id: 'n1', text: 'hello' }] })
    const subject = ctx({
      application: {
        id: 'app-1',
        module: 'recruitment',
        contact: { name: 'Ada' },
        title: 'Ada',
        status: 'completed',
        tab_bucket: 'completed',
        outcome_entity_type: 'candidate',
        outcome_entity_id: 'cand-9',
      },
    })
    expect(notesSubjectKey(subject)).toBe('cand-9')
    await expect(listNotes(subject)).resolves.toEqual({
      available: true,
      items: [{ id: 'n1', text: 'hello' }],
    })
    expect(get).toHaveBeenCalledWith('/candidates/cand-9/notes')
    await addNote(subject, '  next  ')
    expect(post).toHaveBeenCalledWith('/candidates/cand-9/notes', { text: 'next', visibility: 'internal' })
  })

  it('entity candidate subject uses the same owner path', async () => {
    get.mockResolvedValue({ data: [] })
    const subject = ctx({ entity: { resourceType: 'candidate', resourceId: 'cand-2' } })
    expect(notesSubjectKey(subject)).toBe('cand-2')
    await listNotes(subject)
    expect(get).toHaveBeenCalledWith('/candidates/cand-2/notes')
  })
})
