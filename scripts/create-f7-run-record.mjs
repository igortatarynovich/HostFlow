#!/usr/bin/env node

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)
const repoRoot = path.resolve(__dirname, '..')
const ssotPath = path.join(repoRoot, 'docs', 'crm-production-readiness-ssot.md')

const SCENARIO_META = {
  a: {
    label: 'A',
    businessType: 'services',
    steps: [
      'User registered successfully.',
      'Payment completed (or marked BLOCKED if Stripe/webhooks not available).',
      'Business type services selected.',
      'Work email connected.',
      'First client created.',
      'First message sent.',
      'First task created.',
      'Auto-reply configured.',
      'Workflow started end-to-end.',
    ],
  },
  b: {
    label: 'B',
    businessType: 'agency',
    steps: [
      'User registered successfully.',
      'Payment step completed (or marked BLOCKED if Stripe not available).',
      'Business type agency selected.',
      'Ad source connected.',
      'Lead received.',
      'Client created.',
      'Candidate created.',
      'Manager assigned.',
      'Team + roles configured.',
      'Workflow started end-to-end.',
    ],
  },
  c: {
    label: 'C',
    businessType: 'employer',
    steps: [
      'User registered successfully.',
      'Payment step completed (or marked BLOCKED if Stripe not available).',
      'Business type employer selected.',
      'Vacancy created.',
      'Candidate created.',
      'Responsible person assigned.',
      'Statuses configured.',
      'Work email connected.',
      'Hiring workflow started end-to-end.',
    ],
  },
}

function usage(code = 0) {
  const text = [
    'Usage:',
    '  node scripts/create-f7-run-record.mjs --scenario <a|b|c> --env <staging|production> --tenant <slug> --owner "<name/role>" [--date YYYY-MM-DD] [--result PASS|FAIL|BLOCKED|IN_PROGRESS] [--dry-run] [--print-ssot-row] [--append-ssot] [--upsert-ssot] [--sync-board-status] [--no-validate]',
    '',
    'Example:',
    '  node scripts/create-f7-run-record.mjs --scenario b --env staging --tenant demo-agency --owner "Product/QA" --dry-run',
  ].join('\n')
  console.log(text)
  process.exit(code)
}

function parseArgs(argv) {
  const out = {
    scenario: '',
    env: '',
    tenant: '',
    owner: '',
    date: '',
    result: 'IN_PROGRESS',
    dryRun: false,
    printSsotRow: false,
    appendSsot: false,
    upsertSsot: false,
    syncBoardStatus: false,
    validate: true,
  }
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--scenario') out.scenario = String(argv[++i] || '').trim().toLowerCase()
    else if (arg === '--env') out.env = String(argv[++i] || '').trim().toLowerCase()
    else if (arg === '--tenant') out.tenant = String(argv[++i] || '').trim()
    else if (arg === '--owner') out.owner = String(argv[++i] || '').trim()
    else if (arg === '--date') out.date = String(argv[++i] || '').trim()
    else if (arg === '--result') out.result = String(argv[++i] || '').trim().toUpperCase()
    else if (arg === '--dry-run') out.dryRun = true
    else if (arg === '--print-ssot-row') out.printSsotRow = true
    else if (arg === '--append-ssot') out.appendSsot = true
    else if (arg === '--upsert-ssot') out.upsertSsot = true
    else if (arg === '--sync-board-status') out.syncBoardStatus = true
    else if (arg === '--no-validate') out.validate = false
    else if (arg === '--help' || arg === '-h') usage(0)
    else usage(1)
  }
  return out
}

function todayUtc() {
  return new Date().toISOString().slice(0, 10)
}

function safeSlug(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9._-]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function buildContent({ scenario, env, tenant, owner, date, result }) {
  const meta = SCENARIO_META[scenario]
  const lines = []
  lines.push(`# F7 Scenario ${meta.label} Run Record`)
  lines.push('')
  lines.push(`Date: \`${date}\`  `)
  lines.push(`Scenario: \`${meta.label}\`  `)
  lines.push(`Business type: \`${meta.businessType}\`  `)
  lines.push(`Environment: \`${env}\`  `)
  lines.push(`Tenant: \`${tenant}\`  `)
  lines.push(`Owner: \`${owner}\`  `)
  lines.push(`Result: \`${result}\`  `)
  lines.push('Blocker (if any): `N/A`')
  lines.push('')
  lines.push('## Step-by-Step Evidence')
  lines.push('')
  lines.push('| Step | Expected | Actual | Status (`PASS/FAIL/BLOCKED`) | Evidence |')
  lines.push('|---|---|---|---|---|')
  meta.steps.forEach((step, idx) => {
    lines.push(`| ${idx + 1} | ${step} | <observed behavior> | <PASS/FAIL/BLOCKED> | <screenshot/video/log link> |`)
  })
  lines.push('')
  lines.push('## Summary Evidence')
  lines.push('')
  lines.push('- UI evidence: `<links/notes>`')
  lines.push('- API/log evidence: `<links/snippets>`')
  lines.push('- Notes: `<key observations>`')
  lines.push('')
  lines.push('## Issues')
  lines.push('')
  lines.push('- `<BUG-ID / N/A>`')
  lines.push('')
  lines.push('## Sign-off')
  lines.push('')
  lines.push('- Product: `<name>`')
  lines.push('- QA: `<name>`')
  lines.push('')
  return lines.join('\n')
}

function buildSsotRow({ scenario, env, tenant, owner, date, result, outPath }) {
  const meta = SCENARIO_META[scenario]
  const fileName = path.basename(outPath)
  const link = `[${fileName}](${outPath})`
  return `| \`${date}\` | ${meta.label} (\`${meta.businessType}\`) | ${env} | \`${tenant}\` | \`${result}\` | ${link} | ${owner} |`
}

function appendRowToSsot(row, { scenario, env, tenant, date }) {
  if (!fs.existsSync(ssotPath)) {
    throw new Error(`SSOT not found: ${ssotPath}`)
  }
  const text = fs.readFileSync(ssotPath, 'utf-8')
  const startMarker = '### 10.1 Журнал прогонов (операционный)'
  const endMarker = '### 10.2 Next Actions Для `F7`'
  const startIdx = text.indexOf(startMarker)
  const endIdx = text.indexOf(endMarker)
  if (startIdx < 0 || endIdx < 0 || endIdx <= startIdx) {
    throw new Error('Could not locate section 10.1 in SSOT')
  }
  const section = text.slice(startIdx, endIdx)
  const duplicatePattern = new RegExp(
    `\\|\\s*\\\`${date}\\\`\\s*\\|\\s*${SCENARIO_META[scenario].label}\\s*\\([^|]+\\)\\s*\\|\\s*${env}\\s*\\|\\s*\\\`${tenant.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\\`\\s*\\|`,
    'i',
  )
  if (duplicatePattern.test(section)) {
    throw new Error('Duplicate SSOT 10.1 row detected for same date/scenario/env/tenant')
  }
  const insertionPoint = endIdx - 1
  const next = `${text.slice(0, insertionPoint)}${row}\n${text.slice(insertionPoint)}`
  fs.writeFileSync(ssotPath, next, 'utf-8')
}

function escapeRegex(value) {
  return String(value || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function upsertRowInSsot(row, { scenario, env, tenant, date }) {
  if (!fs.existsSync(ssotPath)) {
    throw new Error(`SSOT not found: ${ssotPath}`)
  }
  const text = fs.readFileSync(ssotPath, 'utf-8')
  const startMarker = '### 10.1 Журнал прогонов (операционный)'
  const endMarker = '### 10.2 Next Actions Для `F7`'
  const startIdx = text.indexOf(startMarker)
  const endIdx = text.indexOf(endMarker)
  if (startIdx < 0 || endIdx < 0 || endIdx <= startIdx) {
    throw new Error('Could not locate section 10.1 in SSOT')
  }
  const section = text.slice(startIdx, endIdx)
  const label = SCENARIO_META[scenario].label
  const keyRegex = new RegExp(
    `^\\|\\s*\\\`${escapeRegex(date)}\\\`\\s*\\|\\s*${escapeRegex(label)}\\s*\\([^|]+\\)\\s*\\|\\s*${escapeRegex(env)}\\s*\\|\\s*\\\`${escapeRegex(tenant)}\\\`\\s*\\|.*$`,
    'm',
  )
  const updatedSection = keyRegex.test(section)
    ? section.replace(keyRegex, row)
    : `${section}${row}\n`
  const next = `${text.slice(0, startIdx)}${updatedSection}${text.slice(endIdx)}`
  fs.writeFileSync(ssotPath, next, 'utf-8')
}

function mapRunResultToBoardStatus(result) {
  if (result === 'PASS') return 'PASS'
  if (result === 'BLOCKED') return 'BLOCKED'
  if (result === 'IN_PROGRESS') return 'IN_PROGRESS'
  // FAIL in run-log means scenario is not done yet; keep board as in-progress.
  return 'IN_PROGRESS'
}

function syncBoardStatusInSsot({ scenario, result }) {
  if (!fs.existsSync(ssotPath)) {
    throw new Error(`SSOT not found: ${ssotPath}`)
  }
  const text = fs.readFileSync(ssotPath, 'utf-8')
  const boardHeader = '## 10. F7 Scenario Execution Board (A/B/C)'
  const nextHeader = '### 10.1 Журнал прогонов (операционный)'
  const startIdx = text.indexOf(boardHeader)
  const endIdx = text.indexOf(nextHeader)
  if (startIdx < 0 || endIdx < 0 || endIdx <= startIdx) {
    throw new Error('Could not locate board table section in SSOT')
  }
  const section = text.slice(startIdx, endIdx)
  const scenarioLabel = SCENARIO_META[scenario].label
  const boardStatus = mapRunResultToBoardStatus(result)
  const pattern = new RegExp(`(\\|\\s*${scenarioLabel}\\s*[—-][^|]*\\|\\s*)\\\`[^\\\`]+\\\``)
  if (!pattern.test(section)) {
    throw new Error(`Could not locate board row for scenario ${scenarioLabel}`)
  }
  const updatedSection = section.replace(pattern, `$1\`${boardStatus}\``)
  const next = `${text.slice(0, startIdx)}${updatedSection}${text.slice(endIdx)}`
  fs.writeFileSync(ssotPath, next, 'utf-8')
}

function validateF7RunLog() {
  const validatorPath = path.join(repoRoot, 'scripts', 'check-f7-run-log.mjs')
  const res = spawnSync(process.execPath, [validatorPath], {
    cwd: repoRoot,
    stdio: 'inherit',
  })
  if (res.status !== 0) {
    throw new Error('f7 run-log validation failed after SSOT update')
  }
}

function main() {
  const args = parseArgs(process.argv.slice(2))
  if (!SCENARIO_META[args.scenario]) usage(1)
  if (!['staging', 'production'].includes(args.env)) usage(1)
  if (!args.tenant || !args.owner) usage(1)
  if (args.result && !['PASS', 'FAIL', 'BLOCKED', 'IN_PROGRESS'].includes(args.result)) usage(1)
  if (args.appendSsot && args.upsertSsot) usage(1)
  if (args.dryRun && (args.appendSsot || args.upsertSsot)) usage(1)
  if (args.dryRun && args.syncBoardStatus) usage(1)

  const date = args.date || todayUtc()
  const scenario = args.scenario
  const env = args.env
  const tenantSlug = safeSlug(args.tenant) || 'tenant'
  const outName = `f7-run-${scenario}-${date}-${env}-${tenantSlug}.md`
  const outPath = path.join(repoRoot, 'docs', 'manual-checklist', outName)

  const content = buildContent({
    scenario,
    env,
    tenant: args.tenant,
    owner: args.owner,
    date,
    result: args.result || 'IN_PROGRESS',
  })

  if (args.dryRun) {
    console.log(`Dry run: ${outPath}`)
    if (args.printSsotRow) {
      const row = buildSsotRow({
        scenario,
        env,
        tenant: args.tenant,
        owner: args.owner,
        date,
        result: args.result || 'IN_PROGRESS',
        outPath,
      })
      console.log('SSOT 10.1 row preview:')
      console.log(row)
    }
    return
  }

  if (fs.existsSync(outPath)) {
    console.error(`File already exists: ${outPath}`)
    process.exit(1)
  }
  fs.writeFileSync(outPath, content, 'utf-8')
  console.log(`Created: ${outPath}`)
  const row = buildSsotRow({
    scenario,
    env,
    tenant: args.tenant,
    owner: args.owner,
    date,
    result: args.result || 'IN_PROGRESS',
    outPath,
  })
  if (args.appendSsot) {
    appendRowToSsot(row, { scenario, env, tenant: args.tenant, date })
    console.log('SSOT 10.1 row appended.')
  }
  if (args.upsertSsot) {
    upsertRowInSsot(row, { scenario, env, tenant: args.tenant, date })
    console.log('SSOT 10.1 row upserted.')
  }
  if (args.syncBoardStatus) {
    syncBoardStatusInSsot({ scenario, result: args.result || 'IN_PROGRESS' })
    console.log('SSOT board status synced.')
  }
  if ((args.appendSsot || args.upsertSsot || args.syncBoardStatus) && args.validate) {
    validateF7RunLog()
    console.log('F7 run-log validation passed.')
  }
  if (args.printSsotRow) {
    console.log('SSOT 10.1 row:')
    console.log(row)
  }
}

main()
