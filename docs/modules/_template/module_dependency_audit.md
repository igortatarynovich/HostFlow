# <Module> Dependency Audit

Status: draft  
Date: YYYY-MM-DD

## Audit Scope

1. direct reference internals bypass;
2. direct cross-module imports;
3. delivery/facade contract bypass;
4. legacy wrapper usage;
5. temporary exceptions alignment.

## Current Findings

Must-fix (current):
1. <finding-1>

Allowed baseline notes:
1. <baseline-note-1>

## Temporary Exceptions Linkage

1. <EXC-id-1>
2. <EXC-id-2>

## Guard Scan Commands

```bash
cd /opt/HostFlow && rg -n "<patterns>" backend/app/<paths>
```

```bash
cd /opt/HostFlow && rg -n "EXC-" docs/specs/gates/system_direct_access_exceptions_registry.md
```
