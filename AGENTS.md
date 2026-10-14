# HostFlow Agent Core Rules

These rules apply to every task. They are operational instructions, not a project encyclopedia. Architecture, queue status, gates, migrations, and environment detail stay in `docs/`. File-scoped rules in `.cursor/rules/` attach by the files being edited. Do not load them all up front.

In Cursor Cloud, read `.cursor/rules/cursor-cloud.mdc` before starting services, installing Python packages, or running the app. That file is not part of this always-on context.

1. Canon is authoritative.
   Never override an existing HostFlow contract, architecture decision,
   ownership boundary or accepted gate without explicit instruction.

2. Reuse before invention.
   Existing canonical capabilities and system primitives must be reused.
   Never create a local duplicate, fork, alternative SoT or parallel implementation.

3. Scope is strict.
   Modify only what is required by the task.
   No opportunistic refactoring, cleanup or architecture changes.

4. Explicit user direction overrides implementation assumptions.
   If the user specifies the direction of a migration, source of truth,
   target primitive or required result, preserve that direction exactly.

5. Canonical gap = STOP.
   If the existing system cannot satisfy the requirement without violating
   canon, stop and report the gap. Do not invent a local workaround.

6. Do not claim PASS without evidence.
   Run the applicable repository checks and report failures truthfully.

7. Follow the repository operational canon for git/worktree/PR operations.
