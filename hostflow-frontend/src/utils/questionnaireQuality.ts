export type QuestionnaireQualityBand = 'optimal' | 'long' | 'risky'

export type QuestionnaireQuality = {
  band: QuestionnaireQualityBand
  count: number
}

export function questionnaireQuality(count: number): QuestionnaireQuality {
  const n = Math.max(0, Math.floor(count))
  if (n >= 13) return { band: 'risky', count: n }
  if (n >= 9) return { band: 'long', count: n }
  return { band: 'optimal', count: n }
}
