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

function walkTsFiles(dir, out = []) {
  const IGNORE_DIRS = new Set(['i18n', 'dist', 'node_modules'])
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (IGNORE_DIRS.has(entry.name)) continue
      walkTsFiles(full, out)
      continue
    }
    if (!/\.(ts|tsx)$/.test(entry.name)) continue
    if (/\.(test|spec)\./.test(entry.name) || entry.name.endsWith('.d.ts')) continue
    out.push(full)
  }
  return out
}

function collectMissingUsedKeys(enFlat) {
  const srcDir = path.join(process.cwd(), 'src')
  const tCallRe = /\bt\(\s*(['"`])([^'"`$]+)\1\s*(,\s*\{[\s\S]*?\})?\)/g
  const missing = new Map()
  for (const file of walkTsFiles(srcDir)) {
    const text = fs.readFileSync(file, 'utf8')
    tCallRe.lastIndex = 0
    let m
    while ((m = tCallRe.exec(text))) {
      const key = m[2]
      if (key.includes('${')) continue
      const opts = m[3] || ''
      if (/defaultValue\s*:/.test(opts)) continue
      if (key in enFlat) continue
      const line = text.slice(0, m.index).split('\n').length
      const rel = path.relative(process.cwd(), file)
      if (!missing.has(key)) missing.set(key, [])
      missing.get(key).push(`${rel}:${line}`)
    }
  }
  return missing
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

  const missingUsed = collectMissingUsedKeys(reference.flat)
  if (missingUsed.size) {
    hasError = true
    const lines = [...missingUsed.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([key, refs]) => `  - ${key}  (${refs.slice(0, 2).join(', ')})`)
    console.error(`Used t() keys missing from en.json (no defaultValue):\n${lines.join('\n')}`)
  }

  if (hasError) {
    process.exit(1)
  } else {
    console.log('All locale files are in sync.')
  }
}

main()
