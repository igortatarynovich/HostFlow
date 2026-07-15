import { describe, expect, it } from 'vitest'
import { questionnaireQuality } from '../questionnaireQuality'

describe('questionnaireQuality', () => {
  it('marks small forms as optimal', () => {
    expect(questionnaireQuality(6).band).toBe('optimal')
    expect(questionnaireQuality(8).band).toBe('optimal')
  })

  it('marks medium forms as long', () => {
    expect(questionnaireQuality(9).band).toBe('long')
    expect(questionnaireQuality(12).band).toBe('long')
  })

  it('marks large forms as risky', () => {
    expect(questionnaireQuality(13).band).toBe('risky')
    expect(questionnaireQuality(20).band).toBe('risky')
  })
})
