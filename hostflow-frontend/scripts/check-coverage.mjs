#!/usr/bin/env node
/**
 * Phase 0 #7: frontend coverage ratchet gate.
 *
 * Consumes `coverage/coverage-summary.json` (emitted by the
 * `json-summary` vitest reporter — see `vitest.config.ts`) and enforces:
 *
 *   measured ≥ baseline - tolerance
 *
 * where `baseline` lives in `.coverage-baseline` (single float, 0-100).
 * The audit-plan target is 40% — currently aspirational; the script prints
 * the gap so CI readers see both the hard floor and the north star.
 *
 * Usage:
 *   npm run coverage:check                               # default paths
 *   node scripts/check-coverage.mjs --target 45 --write  # ratchet upward
 */
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
const FRONTEND_ROOT = resolve(__dirname, '..')

const DEFAULTS = {
  summary: resolve(FRONTEND_ROOT, 'coverage/coverage-summary.json'),
  baselineFile: resolve(FRONTEND_ROOT, '.coverage-baseline'),
  tolerance: 0.5,
  target: 40.0,
}

function parseArgs(argv) {
  const out = { ...DEFAULTS, write: false, overrideBaseline: null }
  for (let i = 2; i < argv.length; i += 1) {
    const flag = argv[i]
    const next = argv[i + 1]
    switch (flag) {
      case '--summary':
        out.summary = resolve(next)
        i += 1
        break
      case '--baseline-file':
        out.baselineFile = resolve(next)
        i += 1
        break
      case '--baseline':
        out.overrideBaseline = Number.parseFloat(next)
        i += 1
        break
      case '--tolerance':
        out.tolerance = Number.parseFloat(next)
        i += 1
        break
      case '--target':
        out.target = Number.parseFloat(next)
        i += 1
        break
      case '--write':
      case '--write-baseline':
        out.write = true
        break
      default:
        if (flag.startsWith('--')) {
          console.error(`[check-coverage] unknown flag: ${flag}`)
          process.exit(2)
        }
    }
  }
  return out
}

function readBaseline(path) {
  if (!existsSync(path)) {
    console.error(`[check-coverage] baseline file not found: ${path}`)
    process.exit(2)
  }
  const raw = readFileSync(path, 'utf-8').trim()
  if (!raw) {
    console.error(`[check-coverage] baseline file is empty: ${path}`)
    process.exit(2)
  }
  const value = Number.parseFloat(raw)
  if (Number.isNaN(value)) {
    console.error(
      `[check-coverage] baseline file must contain a single float (got "${raw}"): ${path}`,
    )
    process.exit(2)
  }
  return value
}

function readMeasured(summaryPath) {
  if (!existsSync(summaryPath)) {
    console.error(
      `[check-coverage] coverage summary not found: ${summaryPath}\n` +
        'Run `npm run test:coverage` first (emits coverage/coverage-summary.json).',
    )
    process.exit(2)
  }
  const raw = readFileSync(summaryPath, 'utf-8')
  let doc
  try {
    doc = JSON.parse(raw)
  } catch (err) {
    console.error(`[check-coverage] malformed JSON in ${summaryPath}: ${err.message}`)
    process.exit(2)
  }
  const pct = doc?.total?.lines?.pct
  if (typeof pct !== 'number') {
    console.error(
      `[check-coverage] could not read total.lines.pct from ${summaryPath}`,
    )
    process.exit(2)
  }
  return pct
}

function main() {
  const args = parseArgs(process.argv)
  const baseline =
    args.overrideBaseline != null ? args.overrideBaseline : readBaseline(args.baselineFile)
  const measured = readMeasured(args.summary)
  const floor = baseline - args.tolerance
  const dropped = measured + 1e-9 < floor

  const pad = (n) => n.toFixed(2).padStart(6)
  console.log('='.repeat(60))
  console.log('Phase 0 #7 — frontend coverage gate')
  console.log('-'.repeat(60))
  console.log(`measured : ${pad(measured)} %`)
  console.log(
    `baseline : ${pad(baseline)} %  (from ${args.baselineFile.replace(FRONTEND_ROOT + '/', '')})`,
  )
  console.log(`floor    : ${pad(floor)} %  (baseline - tolerance ${args.tolerance}pp)`)
  console.log(`target   : ${pad(args.target)} %  (audit plan north star)`)
  console.log('='.repeat(60))

  if (dropped) {
    console.error(
      `[check-coverage] FAIL — coverage ${measured.toFixed(2)}% dropped below ` +
        `the floor ${floor.toFixed(2)}% (baseline ${baseline.toFixed(2)}%).`,
    )
    console.error(
      '  → Either add tests to restore coverage, or if the drop is ' +
        'intentional, explicitly lower the baseline in a reviewable commit.',
    )
    process.exit(1)
  }

  if (args.write && measured > baseline + args.tolerance) {
    const newBaseline = Number((measured - args.tolerance).toFixed(2))
    writeFileSync(args.baselineFile, `${newBaseline.toFixed(2)}\n`, 'utf-8')
    console.log(
      `[check-coverage] ratcheted baseline ${baseline.toFixed(2)}% → ` +
        `${newBaseline.toFixed(2)}%`,
    )
  }

  if (measured + 1e-9 < args.target) {
    const gap = (args.target - measured).toFixed(2)
    console.log(
      `[check-coverage] OK — ${gap}pp below the audit-plan target of ${args.target.toFixed(2)}%.`,
    )
  } else {
    console.log(
      `[check-coverage] OK — target ${args.target.toFixed(2)}% met or exceeded.`,
    )
  }
}

main()
