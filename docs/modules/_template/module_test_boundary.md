# <Module> Test Boundary

Status: draft  
Date: YYYY-MM-DD

## Mandatory Boundary Test Types

1. import-boundary tests;
2. contract compatibility tests;
3. guard scans;
4. regression tests for boundary diffs.

## Focused Boundary Pack

```bash
cd /opt/HostFlow && pytest -q <focused-tests>
```

## Optional Extended Pack

```bash
cd /opt/HostFlow && pytest -q <extended-tests>
```

## PASS Criteria

1. no forbidden direct imports;
2. contract-only cross-module access;
3. scans/tests green or baseline-note stable.

## STOP Criteria

1. direct bypass appears;
2. contract bypass without exception;
3. regressions without gate decision.
