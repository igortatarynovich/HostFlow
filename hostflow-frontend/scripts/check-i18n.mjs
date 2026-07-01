import fs from 'node:fs'
import path from 'node:path'

const LOCALES = ['en', 'ru', 'pl']
const baseDir = path.join(process.cwd(), 'src', 'i18n')

function loadLocale(locale) {
  const file = path.join(baseDir, `${locale}.json`)
  return JSON.parse(fs.readFileSync(file, 'utf-8'))
}

function flatten(obj, prefix = '') {
  const acc = {}
  Object.entries(obj ?? {}).forEach(([key, value]) => {
    const nextKey = prefix ? `${prefix}.${key}` : key
    if (value && typeof value === 'object' && !Array.isArray(value)) {
      Object.assign(acc, flatten(value, nextKey))
    } else {
      acc[nextKey] = String(value)
    }
  })
  return acc
}

function main() {
  const maps = LOCALES.map((locale) => ({ locale, flat: flatten(loadLocale(locale)) }))
  const reference = maps[0]
  let hasError = false

  maps.slice(1).forEach(({ locale, flat }) => {
    const missing = Object.keys(reference.flat).filter((key) => flat[key] === undefined)
    const extra = Object.keys(flat).filter((key) => reference.flat[key] === undefined)
    if (missing.length) {
      hasError = true
      console.error(`[${locale}] missing keys:\n  - ${missing.join('\n  - ')}`)
    }
    if (extra.length) {
      hasError = true
      console.error(`[${locale}] extra keys:\n  - ${extra.join('\n  - ')}`)
    }
  })

  if (hasError) {
    process.exit(1)
  } else {
    console.log('All locale files are in sync.')
  }
}

main()
