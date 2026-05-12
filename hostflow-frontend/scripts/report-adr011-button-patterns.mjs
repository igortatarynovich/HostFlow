/**
 * ADR-011 §6–7: inventory of native `<button>` opening tags that may lack `.btn*` styling.
 *
 * Uses the **TypeScript** parser (same as the project) so multiline attributes, template
 * literals, and JSX expressions are handled like the compiler.
 *
 *   node scripts/report-adr011-button-patterns.mjs           # exit 0, summary + JSON report
 *   node scripts/report-adr011-button-patterns.mjs --fail   # exit 1 if missing count > scripts/adr011-button-baseline.json
 *
 * Per-opening suppress: `adr011-button-ignore` on the same line as the opening tag (or use btn classes).
 */
import fs from 'node:fs'
import path from 'node:path'
import ts from 'typescript'

const root = process.cwd()
const srcDir = path.join(root, 'src')
const fail = process.argv.includes('--fail')
const baselineFile = path.join(root, 'scripts', 'adr011-button-baseline.json')

const IGNORE_DIRS = new Set(['dist', 'node_modules', 'i18n'])
const IGNORE_FILES = [/\.test\./, /\.spec\./, /\.d\.ts$/]

function hasBtnToken(tagText) {
  return /btn[-.]/.test(tagText) || /\bbtn\b/.test(tagText)
}

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

function scriptKindForFile(filePath) {
  return filePath.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS
}

function lineNumberAtPosition(sf, pos) {
  return sf.getLineAndCharacterOfPosition(pos).line + 1
}

function collectButtonOpens(text, filePath) {
  const kind = scriptKindForFile(filePath)
  const sf = ts.createSourceFile(filePath, text, ts.ScriptTarget.Latest, true, kind)
  const out = []

  function visit(node) {
    const isButtonOpen =
      (ts.isJsxOpeningElement(node) || ts.isJsxSelfClosingElement(node)) &&
      ts.isIdentifier(node.tagName) &&
      node.tagName.escapedText === 'button'

    if (isButtonOpen) {
      const start = node.getStart(sf)
      const end = node.getEnd()
      const raw = text.slice(start, end)
      out.push({ raw, line: lineNumberAtPosition(sf, start) })
    }
    ts.forEachChild(node, visit)
  }

  visit(sf)
  return out
}

function main() {
  const files = walk(srcDir)
  const perFile = []
  let totalTags = 0
  let missingToken = 0

  for (const file of files) {
    const text = fs.readFileSync(file, 'utf8')
    const lines = text.split(/\r?\n/)
    const opens = collectButtonOpens(text, file)
    totalTags += opens.length

    const hits = []
    for (const { raw, line } of opens) {
      if (hasBtnToken(raw)) continue
      const lineText = lines[line - 1] ?? ''
      if (lineText.includes('adr011-button-ignore')) continue
      const snippet = (raw.includes('\n') ? lineText : raw).trim().slice(0, 220)
      hits.push({ line, snippet })
    }
    missingToken += hits.length
    if (hits.length) perFile.push({ file, rel: path.relative(root, file), hits })
  }

  perFile.sort((a, b) => b.hits.length - a.hits.length)

  console.log(
    `ADR-011 §6–7: <button> opens without btn token (TypeScript AST): ${missingToken} of ${totalTags}`,
  )
  for (const item of perFile.slice(0, 40)) {
    console.log(`${String(item.hits.length).padStart(4, ' ')}  ${item.rel}`)
  }
  if (perFile.length > 40) console.log(`… ${perFile.length - 40} more files`)

  const outPath = path.join(root, 'adr011-button-patterns-report.json')
  fs.writeFileSync(
    outPath,
    JSON.stringify(
      {
        generated_at: new Date().toISOString(),
        note: 'Intrinsic JSX <button> / <button /> via TypeScript AST. Missing btn- or word btn in opening tag text.',
        total_button_opens: totalTags,
        opens_missing_btn_token: missingToken,
        files: perFile.map((x) => ({
          file: x.rel,
          count: x.hits.length,
          examples: x.hits.slice(0, 12),
        })),
      },
      null,
      2,
    ) + '\n',
    'utf8',
  )
  console.log(`Report: ${path.relative(root, outPath)}`)

  if (fail) {
    let maxMissing
    try {
      const raw = JSON.parse(fs.readFileSync(baselineFile, 'utf8'))
      maxMissing = Number(raw.maxMissingBtnOpens)
    } catch {
      console.error(`ADR-011 §6–7: missing or invalid ${path.relative(root, baselineFile)} (required with --fail)`)
      process.exit(1)
    }
    if (!Number.isFinite(maxMissing)) {
      console.error('ADR-011 §6–7: maxMissingBtnOpens must be a number in adr011-button-baseline.json')
      process.exit(1)
    }
    if (missingToken > maxMissing) {
      console.error(
        `ADR-011 §6–7 button gate: ${missingToken} <button> opens without btn token > baseline ${maxMissing}. ` +
          'Add `.btn*` classes, suppress with adr011-button-ignore on the line, or lower baseline only when reducing debt.',
      )
      process.exit(1)
    }
  }
}

main()
