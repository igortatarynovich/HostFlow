#!/usr/bin/env node
/**
 * Fail if npm audit reports high/critical on auth/network-sensitive runtime deps.
 * Dev-only transitive issues (vite, rollup, …) are ignored unless the package name matches.
 */

import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND = join(__dirname, "..", "..", "hostflow-frontend");

const SENSITIVE = new Set(
  [
    "axios",
    "follow-redirects",
    "@remix-run/router",
    "react-router",
    "react-router-dom",
    "@sentry/react",
    "jws",
    "jsonwebtoken",
    "oauth4webapi",
    "openid-client",
  ].map((s) => s.toLowerCase()),
);

function sevRank(s) {
  if (s === "critical") return 3;
  if (s === "high") return 2;
  if (s === "moderate") return 1;
  return 0;
}

function main() {
  const r = spawnSync("npm", ["audit", "--json"], {
    cwd: FRONTEND,
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
  const raw = r.stdout || "";
  if (!raw.trim()) {
    console.error("npm_audit_gate: empty npm audit output", r.stderr);
    process.exit(1);
  }
  const data = JSON.parse(raw);
  const vulns = data.vulnerabilities || {};
  const hits = [];

  for (const [name, meta] of Object.entries(vulns)) {
    const sev = (meta.severity || "").toLowerCase();
    if (sevRank(sev) < 2) continue;
    const key = name.toLowerCase();
    if (!SENSITIVE.has(key)) continue;
    hits.push({ name, severity: sev, via: meta.via });
  }

  if (hits.length) {
    console.error(
      "High/critical vulnerabilities in sensitive runtime packages:\n",
      JSON.stringify(hits, null, 2),
    );
    process.exit(1);
  }
  console.log("npm_audit_gate: no high/critical issues in sensitive packages.");
}

main();
