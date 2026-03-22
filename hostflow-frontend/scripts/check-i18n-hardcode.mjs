import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const srcDir = path.join(root, 'src')

const IGNORE_DIRS = new Set(['i18n', 'dist', 'dist.bak', 'node_modules'])
const IGNORE_FILES = [/\.test\./, /\.spec\./, /\.d\.ts$/]

function walk(dir, out = []) {
  const entries = fs.readdirSync(dir, { withFileTypes: true })
  for (const entry of entries) {
    const full = path.join(dir, entry.name)
    if (entry.isDirectory()) {
      if (IGNORE_DIRS.has(entry.name)) continue
      walk(full, out)
      continue
    }
    if (!/\.(ts|tsx)$/.test(entry.name)) continue
    if (IGNORE_FILES.some((re) => re.test(entry.name))) continue
    out.push(full)
  }
  return out
}

const JSX_TEXT_RE = />\s*([^<{][^<{]*[A-Za-zА-Яа-яЁё][^<{]*)\s*</g
const ATTR_RE = /\b(placeholder|title|aria-label|label)\s*=\s*("([^"]*[A-Za-zА-Яа-яЁё][^"]*)"|'([^']*[A-Za-zА-Яа-яЁё][^']*)')/g

function shouldIgnoreText(text) {
  const trimmed = text.trim()
  if (!trimmed) return true
  if (trimmed.length < 2) return true
  if (/^[\W\d_]+$/.test(trimmed)) return true
  if (/^(https?:\/\/|\/api\/|[A-Za-z0-9_.-]+\.[A-Za-z]{2,})/.test(trimmed)) return true
  return false
}

function collectFindings(file) {
  const text = fs.readFileSync(file, 'utf8')
  const lines = text.split(/\r?\n/)
  const findings = []

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]
    if (line.includes(' t(') || line.includes('{t(') || line.includes('/* i18n-ignore */')) continue

    let m
    JSX_TEXT_RE.lastIndex = 0
    while ((m = JSX_TEXT_RE.exec(line))) {
      const candidate = (m[1] || '').trim()
      if (shouldIgnoreText(candidate)) continue
      findings.push({
        file,
        line: i + 1,
        kind: 'jsx-text',
        text: candidate,
      })
    }

    ATTR_RE.lastIndex = 0
    while ((m = ATTR_RE.exec(line))) {
      const attrName = m[1]
      const candidate = (m[3] ?? m[4] ?? '').trim()
      if (shouldIgnoreText(candidate)) continue
      findings.push({
        file,
        line: i + 1,
        kind: `attr:${attrName}`,
        text: candidate,
      })
    }
  }

  return findings
}

function main() {
  const files = walk(srcDir)
  const all = files.flatMap((file) => collectFindings(file))
  const byFile = new Map()
  for (const item of all) {
    const arr = byFile.get(item.file) || []
    arr.push(item)
    byFile.set(item.file, arr)
  }

  const sorted = [...byFile.entries()].sort((a, b) => b[1].length - a[1].length)
  console.log(`Potential hardcoded UI strings: ${all.length}`)
  for (const [file, items] of sorted.slice(0, 200)) {
    const rel = path.relative(root, file)
    console.log(`${items.length.toString().padStart(4, ' ')}  ${rel}`)
  }

  const reportFile = path.join(root, 'i18n-hardcode-report.json')
  fs.writeFileSync(
    reportFile,
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        total: all.length,
        files: sorted.map(([file, items]) => ({
          file: path.relative(root, file),
          count: items.length,
          examples: items.slice(0, 20).map((x) => ({ line: x.line, kind: x.kind, text: x.text })),
        })),
      },
      null,
      2,
    ) + '\n',
    'utf8',
  )
  console.log(`Report saved to ${path.relative(root, reportFile)}`)
}

main()
