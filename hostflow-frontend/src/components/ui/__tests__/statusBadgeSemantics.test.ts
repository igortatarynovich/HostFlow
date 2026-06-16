// @vitest-environment node
import { describe, expect, it } from 'vitest'

import {
  documentSeverityToSemantic,
  nextActionPriorityToSemantic,
  stageSemanticForCode,
} from '../statusBadgeSemantics'

describe('stageSemanticForCode', () => {
  it('maps known candidate stages', () => {
    expect(stageSemanticForCode('employed')).toBe('success')
    expect(stageSemanticForCode('rejected')).toBe('danger')
    expect(stageSemanticForCode('contacted')).toBe('brand')
  })

  it('maps vacancy stages', () => {
    expect(stageSemanticForCode('open')).toBe('success')
    expect(stageSemanticForCode('paused')).toBe('warning')
    expect(stageSemanticForCode('closed')).toBe('neutral')
  })

  it('falls back to neutral', () => {
    expect(stageSemanticForCode('unknown_stage')).toBe('neutral')
    expect(stageSemanticForCode(null)).toBe('neutral')
  })
})

describe('nextActionPriorityToSemantic', () => {
  it('maps priorities', () => {
    expect(nextActionPriorityToSemantic('critical')).toBe('danger')
    expect(nextActionPriorityToSemantic('high')).toBe('warning')
    expect(nextActionPriorityToSemantic('normal')).toBe('info')
    expect(nextActionPriorityToSemantic('idle')).toBe('neutral')
  })

  it('falls back to neutral', () => {
    expect(nextActionPriorityToSemantic(undefined)).toBe('neutral')
    expect(nextActionPriorityToSemantic('unknown')).toBe('neutral')
  })
})

describe('documentSeverityToSemantic', () => {
  it('maps severities', () => {
    expect(documentSeverityToSemantic('ok')).toBe('success')
    expect(documentSeverityToSemantic('warn')).toBe('warning')
    expect(documentSeverityToSemantic('bad')).toBe('danger')
    expect(documentSeverityToSemantic('info')).toBe('info')
  })
})
