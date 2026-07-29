#!/usr/bin/env python3
"""
Merge gate: keep CRM tenant DB bind fail-closed and auth-covered.

Checks:
1. ``get_db_with_tenant`` in ``backend/app/db/deps.py`` must depend on
   ``get_current_user`` (not ``get_current_user_optional``).
2. ``get_db_with_meta_leads_effective_tenant`` must depend on ``get_current_user``.
3. Every ``Depends(get_db_with_tenant_public)`` call site must be listed in
   ``scripts/security/tenant_bind_public_allowlist.txt`` (signed webhooks only).
4. Every FastAPI route that declares ``X-Tenant-Id`` (or uses a tenant-bind
   dependency that does not itself require auth) must also require auth —
   unless listed in ``scripts/security/tenant_header_public_allowlist.txt``.

Run from repo root::

    python3 scripts/security/check_tenant_bind_auth.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPS_FILE = REPO_ROOT / "backend" / "app" / "db" / "deps.py"
META_LEADS_DEP_FILE = REPO_ROOT / "backend" / "app" / "db" / "meta_leads_tenant_dep.py"
SCAN_ROOT = REPO_ROOT / "backend" / "app"
PUBLIC_ALLOWLIST_FILE = REPO_ROOT / "scripts" / "security" / "tenant_bind_public_allowlist.txt"
HEADER_ALLOWLIST_FILE = (
    REPO_ROOT / "scripts" / "security" / "tenant_header_public_allowlist.txt"
)

PUBLIC_DEP = re.compile(r"Depends\(\s*get_db_with_tenant_public\s*\)")

ROUTE_DECORATOR_ATTRS = frozenset(
    {"get", "post", "put", "patch", "delete", "options", "head", "api_route"}
)

# Dependencies that imply an authenticated CRM principal (or fail-closed bind).
AUTH_DEP_NAMES = frozenset(
    {
        "get_current_user",
        "require_roles",
        "require_any_role",
        "require_superadmin",
        "require_platform_admin",
        "get_db_with_tenant",  # fail-closed: Depends(get_current_user)
        "get_db_with_meta_leads_effective_tenant",  # Depends(get_current_user)
    }
)

# Explicit Header X-Tenant-Id without auth is the residual class we close.
TENANT_HEADER_ALIASES = frozenset({"X-Tenant-Id", "x-tenant-id"})


def _load_allowlist(path: Path) -> set[str]:
    if not path.is_file():
        print(f"ERROR: missing allowlist file: {path}", file=sys.stderr)
        sys.exit(2)
    out: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line.replace("\\", "/"))
    return out


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _depends_callee(node: ast.AST) -> str | None:
    """Return the dependency callable name inside Depends(...), if any."""
    if not isinstance(node, ast.Call):
        return None
    if _call_name(node.func) != "Depends":
        return None
    if not node.args:
        return None
    inner = node.args[0]
    if isinstance(inner, ast.Call):
        return _call_name(inner.func)
    return _call_name(inner)


def _header_is_tenant_id(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if _call_name(node.func) != "Header":
        return False
    for kw in node.keywords:
        if kw.arg == "alias" and isinstance(kw.value, ast.Constant):
            if str(kw.value.value) in TENANT_HEADER_ALIASES:
                return True
    return False


def _iter_default_nodes(fn: ast.AsyncFunctionDef | ast.FunctionDef) -> list[ast.AST]:
    args = fn.args
    out: list[ast.AST] = []
    out.extend(args.defaults)
    out.extend(args.kw_defaults)  # type: ignore[arg-type]
    return [n for n in out if n is not None]


def _fn_dep_names(fn: ast.AsyncFunctionDef | ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for default in _iter_default_nodes(fn):
        dep = _depends_callee(default)
        if dep:
            names.add(dep)
    return names


def _fn_has_tenant_header(fn: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    for default in _iter_default_nodes(fn):
        if _header_is_tenant_id(default):
            return True
    return False


def _is_route_function(fn: ast.AsyncFunctionDef | ast.FunctionDef) -> bool:
    for dec in fn.decorator_list:
        # @router.get / @app.post / @router.api_route
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Attribute) and target.attr in ROUTE_DECORATOR_ATTRS:
            return True
    return False


def _route_router_names(fn: ast.AsyncFunctionDef | ast.FunctionDef) -> set[str]:
    """Return router variable names used in decorators (e.g. ``router`` in @router.get)."""
    names: set[str] = set()
    for dec in fn.decorator_list:
        target = dec.func if isinstance(dec, ast.Call) else dec
        if isinstance(target, ast.Attribute) and target.attr in ROUTE_DECORATOR_ATTRS:
            if isinstance(target.value, ast.Name):
                names.add(target.value.id)
    return names


def _resolve_import_aliases(tree: ast.AST) -> dict[str, str]:
    """Map local name → original imported name for auth/tenant deps."""
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                local = alias.asname or alias.name
                aliases[local] = alias.name
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name
                aliases[local] = alias.name
    return aliases


def _canonical_deps(local_deps: set[str], aliases: dict[str, str]) -> set[str]:
    return {aliases.get(name, name) for name in local_deps}


def _apirouter_dependencies(
    tree: ast.AST, aliases: dict[str, str]
) -> dict[str, set[str]]:
    """Map router variable name → canonical dep names from APIRouter(dependencies=[...])."""
    out: dict[str, set[str]] = {}
    for node in tree.body if isinstance(tree, ast.Module) else []:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if not isinstance(node.value, ast.Call):
            continue
        if _call_name(node.value.func) != "APIRouter":
            continue
        router_var = node.targets[0].id
        deps: set[str] = set()
        for kw in node.value.keywords:
            if kw.arg != "dependencies" or not isinstance(kw.value, ast.List):
                continue
            for elt in kw.value.elts:
                dep = _depends_callee(elt)
                if dep:
                    deps.add(aliases.get(dep, dep))
        out[router_var] = deps
    return out


def _check_fail_closed_user_dep(
    path: Path, fn_name: str, *, expect: str = "get_current_user"
) -> list[str]:
    errors: list[str] = []
    rel = path.relative_to(REPO_ROOT).as_posix()
    if not path.is_file():
        return [f"missing {rel}"]
    src = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(src)
    except SyntaxError as exc:
        return [f"{rel} parse error: {exc}"]

    fn: ast.AsyncFunctionDef | ast.FunctionDef | None = None
    for node in tree.body:
        if isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)) and node.name == fn_name:
            fn = node
            break
    if fn is None:
        return [f"{fn_name}() not found in {rel}"]

    args = fn.args
    defaults = list(args.defaults)
    all_pos = list(args.posonlyargs) + list(args.args)
    default_map: dict[str, str] = {}
    if defaults:
        paired = all_pos[-len(defaults) :]
        for arg, default in zip(paired, defaults):
            default_map[arg.arg] = ast.get_source_segment(src, default) or ast.dump(default)

    # Prefer parameter named ``user`` / ``ctx`` / ``current_user``.
    user_default = ""
    for key in ("user", "ctx", "current_user"):
        if key in default_map:
            user_default = default_map[key]
            break
    if not user_default:
        # Fallback: any default containing Depends(...)
        for val in default_map.values():
            if "Depends(" in val and "get_current_user" in val:
                user_default = val
                break

    if "get_current_user_optional" in user_default:
        errors.append(
            f"{fn_name} must not use get_current_user_optional "
            f"(anonymous X-Tenant-Id bind is forbidden) [{rel}]"
        )
    if not re.search(rf"Depends\(\s*{re.escape(expect)}\s*\)", user_default):
        errors.append(
            f"{fn_name}(user/ctx=...) must be Depends({expect}); "
            f"got: {user_default!r} [{rel}]"
        )
    return errors


def _check_public_allowlist(allow: set[str]) -> list[str]:
    violations: list[str] = []
    seen: set[str] = set()
    for path in sorted(SCAN_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            return [f"ERROR reading {rel}: {exc}"]
        if "get_db_with_tenant_public" not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if stripped.startswith("async def get_db_with_tenant_public") or stripped.startswith(
                "def get_db_with_tenant_public"
            ):
                continue
            if "import" in stripped and "get_db_with_tenant_public" in stripped:
                continue
            if "get_db_with_tenant_public" not in stripped:
                continue
            if "Depends(" not in stripped and "= get_db_with_tenant_public" not in stripped:
                continue
            key = f"{rel}:{lineno}"
            seen.add(rel)
            if rel not in allow:
                violations.append(f"{key}: {stripped}")
    for rel in sorted(allow - seen):
        path = REPO_ROOT / rel
        if not path.is_file():
            violations.append(f"allowlist entry missing on disk: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        if "get_db_with_tenant_public" not in text:
            violations.append(f"allowlist entry unused (no get_db_with_tenant_public): {rel}")
    return violations


def _allowlisted(rel: str, fn_name: str, allow: set[str]) -> bool:
    if rel in allow:
        return True
    if f"{rel}:{fn_name}" in allow:
        return True
    return False


def _check_tenant_header_routes(allow: set[str]) -> list[str]:
    """Flag route handlers with X-Tenant-Id (or optional-auth tenant header) without auth."""
    violations: list[str] = []
    seen_keys: set[str] = set()

    for path in sorted(SCAN_ROOT.rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        # Dependency definitions themselves are not HTTP routes.
        if rel in {
            "backend/app/db/deps.py",
            "backend/app/db/meta_leads_tenant_dep.py",
        }:
            continue
        try:
            src = path.read_text(encoding="utf-8")
        except OSError as exc:
            return [f"ERROR reading {rel}: {exc}"]
        if "X-Tenant-Id" not in src and "get_current_user_optional" not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError as exc:
            return [f"{rel} parse error: {exc}"]

        aliases = _resolve_import_aliases(tree)
        router_deps = _apirouter_dependencies(tree, aliases)

        for node in tree.body:
            if not isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                continue
            if not _is_route_function(node):
                continue

            if not _fn_has_tenant_header(node):
                continue

            local_deps = _fn_dep_names(node)
            canon_deps = _canonical_deps(local_deps, aliases)
            for router_name in _route_router_names(node):
                canon_deps |= router_deps.get(router_name, set())

            # get_current_user_optional alone is NOT auth for tenant-bound data.
            is_authed = bool(canon_deps & AUTH_DEP_NAMES)

            key = f"{rel}:{node.name}"
            seen_keys.add(key)
            if is_authed:
                continue
            if _allowlisted(rel, node.name, allow):
                continue
            violations.append(
                f"{key}: declares X-Tenant-Id without required auth dependency "
                f"(deps={sorted(canon_deps)})"
            )

    # Drift: allowlist entries that no longer match a route.
    for entry in sorted(allow):
        if entry in seen_keys:
            continue
        if ":" not in entry:
            # File-level allowlist: require at least one matching route in that file.
            path = REPO_ROOT / entry
            if not path.is_file():
                violations.append(f"header allowlist entry missing on disk: {entry}")
                continue
            # Presence of X-Tenant-Id in file is enough for file-level entries.
            text = path.read_text(encoding="utf-8")
            if "X-Tenant-Id" not in text:
                violations.append(f"header allowlist entry unused (no X-Tenant-Id): {entry}")
            continue
        # function-level unused
        violations.append(f"header allowlist entry unused (no matching route): {entry}")

    return violations


def main() -> int:
    public_allow = _load_allowlist(PUBLIC_ALLOWLIST_FILE)
    header_allow = _load_allowlist(HEADER_ALLOWLIST_FILE)

    errors: list[str] = []
    errors.extend(_check_fail_closed_user_dep(DEPS_FILE, "get_db_with_tenant"))
    errors.extend(
        _check_fail_closed_user_dep(
            META_LEADS_DEP_FILE, "get_db_with_meta_leads_effective_tenant"
        )
    )
    errors.extend(_check_public_allowlist(public_allow))
    errors.extend(_check_tenant_header_routes(header_allow))

    if errors:
        print(
            "Tenant bind auth gate failed.\n"
            "CRM routes must use fail-closed get_db_with_tenant (authenticated).\n"
            "Routes that declare X-Tenant-Id need auth (or an allowlisted public reason).\n"
            "Anonymous signed webhooks must use get_db_with_tenant_public and be allowlisted.\n"
            "See docs/security/runtime-roadmap.md\n",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
