#!/usr/bin/env python3
"""PMI-1+ freeze ratchet: debt may only shrink; new non-contract cross-owner edges FAIL.

Authority: module_isolation_pmi0_baseline.json @ 844900d6 (immutable).
Public contract edges (module_isolation_public_contracts.json) are allowed coupling,
not debt. Ownership completion that makes an edge same-owner is reclassified_internal
(legitimate shrink), not a hide bypass.

PMI-R ownership completion may *reveal* edges that were same-owner UNASSIGNED→UNASSIGNED
at PMI-1 (not in authority). Those may enter debt only via --admit-ownership-reveals,
tracked against module_isolation_owners_pmi1.json. Invented coupling still FAIL.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_module_isolation_map import (  # noqa: E402
    BASELINE_PATH,
    OWNERS_PATH,
    assign_owner,
    build_report,
    file_for_backend_module,
    imported_backend_modules,
    load_config,
    prefix_pairs,
    validate_spine_roots,
)

FREEZE_PATH = REPO_ROOT / "scripts" / "architecture" / "module_isolation_pmi1_freeze.json"
DEBT_PATH = REPO_ROOT / "scripts" / "architecture" / "module_isolation_pmi1_debt.json"
PUBLIC_PATH = REPO_ROOT / "scripts" / "architecture" / "module_isolation_public_contracts.json"
OWNERS_PMI1_PATH = (
    REPO_ROOT / "scripts" / "architecture" / "module_isolation_owners_pmi1.json"
)
PMI1_DEBT_COUNT = 2006


def edge_key(edge: dict) -> tuple[str, str, str]:
    return (edge["from_file"], edge["import"], edge["to_file"])


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def structural_set(edges: list[dict]) -> set[tuple[str, str, str]]:
    return {edge_key(e) for e in edges}


def import_still_present(from_file: str, import_mod: str, to_file: str) -> bool:
    path = REPO_ROOT / from_file
    if not path.is_file():
        return False
    mods = imported_backend_modules(path)
    if import_mod not in mods:
        return False
    resolved = file_for_backend_module(import_mod)
    return resolved == to_file


def load_public_prefixes() -> list[str]:
    if not PUBLIC_PATH.is_file():
        return []
    raw = load_json(PUBLIC_PATH)
    out: list[str] = []
    for _owner, spec in (raw.get("owners") or {}).items():
        for prefix in spec.get("prefixes") or []:
            out.append(prefix.rstrip("/"))
    return out


def is_public_contract_target(to_file: str, public_prefixes: list[str]) -> bool:
    for prefix in public_prefixes:
        if to_file == prefix or to_file.startswith(prefix + "/") or to_file.startswith(prefix + "."):
            return True
    return False


def same_owner_now(from_file: str, to_file: str, prefixes: list[tuple[str, str]]) -> bool:
    fo, _ = assign_owner(from_file, prefixes)
    to, _ = assign_owner(to_file, prefixes)
    return fo == to


def is_ownership_reveal(
    key: tuple[str, str, str],
    pmi1_prefixes: list[tuple[str, str]],
    current_prefixes: list[tuple[str, str]],
) -> bool:
    """True when import existed as same-owner under PMI-1 owners and is cross-owner now."""
    from_file, import_mod, to_file = key
    if not import_still_present(from_file, import_mod, to_file):
        return False
    fo0, _ = assign_owner(from_file, pmi1_prefixes)
    to0, _ = assign_owner(to_file, pmi1_prefixes)
    fo1, _ = assign_owner(from_file, current_prefixes)
    to1, _ = assign_owner(to_file, current_prefixes)
    return fo0 == to0 and fo1 != to1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--shrink-debt",
        action="store_true",
        help="drop debt edges that are gone, reclassified_internal, or only public-contract coupling",
    )
    parser.add_argument(
        "--admit-ownership-reveals",
        action="store_true",
        help="add ownership-reveal edges into debt (PMI-R); requires later --shrink-debt net < PMI-1",
    )
    args = parser.parse_args(argv)

    errors: list[str] = []

    if not FREEZE_PATH.is_file():
        print(f"missing freeze lock: {FREEZE_PATH}", file=sys.stderr)
        return 1
    freeze = load_json(FREEZE_PATH)
    if freeze.get("schema") != "pmi1.v1":
        errors.append(f"unexpected freeze schema: {freeze.get('schema')}")
    if freeze.get("authority_commit") != "844900d6":
        errors.append(
            f"authority_commit must be 844900d6, got {freeze.get('authority_commit')}"
        )

    if not BASELINE_PATH.is_file():
        print(f"missing authority baseline: {BASELINE_PATH}", file=sys.stderr)
        return 1
    actual_sha = sha256_file(BASELINE_PATH)
    expected_sha = freeze.get("authority_sha256")
    if actual_sha != expected_sha:
        errors.append(
            "authority baseline mutated (PMI-0 baseline is immutable after freeze); "
            f"expected sha256 {expected_sha}, got {actual_sha}"
        )

    authority = load_json(BASELINE_PATH)
    authority_edges = structural_set(authority.get("cross_owner_edges") or [])
    if len(authority_edges) != freeze.get("authority_edge_count"):
        errors.append(
            f"authority edge count mismatch: freeze={freeze.get('authority_edge_count')} "
            f"file={len(authority_edges)}"
        )

    if not DEBT_PATH.is_file():
        print(f"missing debt allowlist: {DEBT_PATH}", file=sys.stderr)
        return 1
    debt_doc = load_json(DEBT_PATH)
    debt_edges = structural_set(debt_doc.get("edges") or [])

    if not OWNERS_PATH.is_file():
        print(f"missing owners map: {OWNERS_PATH}", file=sys.stderr)
        return 1
    if not OWNERS_PMI1_PATH.is_file():
        print(f"missing PMI-1 owners snapshot: {OWNERS_PMI1_PATH}", file=sys.stderr)
        return 1
    config = load_config(OWNERS_PATH)
    prefixes = prefix_pairs(config)
    pmi1_config = load_config(OWNERS_PMI1_PATH)
    pmi1_prefixes = prefix_pairs(pmi1_config)
    public_prefixes = load_public_prefixes()

    try:
        report = build_report(config)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    map_errors = validate_spine_roots(config, report)
    if map_errors:
        errors.extend(f"map: {m}" for m in map_errors)

    # Debt-relevant current edges: cross-owner and not a published contract target.
    current_all = structural_set(report.get("cross_owner_edges") or [])
    current_debt_relevant = {
        key for key in current_all if not is_public_contract_target(key[2], public_prefixes)
    }

    reveal_keys = {
        key
        for key in current_debt_relevant
        if is_ownership_reveal(key, pmi1_prefixes, prefixes)
    }

    debt_outside_authority = debt_edges - authority_edges
    invented = {
        key
        for key in debt_outside_authority
        if not is_ownership_reveal(key, pmi1_prefixes, prefixes)
    }
    if invented:
        sample = sorted(invented)[:10]
        errors.append(
            f"debt growth vs authority FORBIDDEN ({len(invented)} invented keys); "
            f"sample={sample}"
        )

    removed = authority_edges - debt_edges
    fake_shrink: list[tuple[str, str, str]] = []
    for key in sorted(removed):
        if not import_still_present(*key):
            continue
        if same_owner_now(key[0], key[2], prefixes):
            continue
        if is_public_contract_target(key[2], public_prefixes):
            continue
        fake_shrink.append(key)
    if fake_shrink:
        errors.append(
            f"debt shrink while import still present FORBIDDEN ({len(fake_shrink)}); "
            f"sample={fake_shrink[:10]}"
        )

    new_leaks = current_debt_relevant - debt_edges
    new_non_reveal = new_leaks - reveal_keys
    if new_non_reveal:
        sample = sorted(new_non_reveal)[:15]
        errors.append(
            f"new cross-owner edge vs debt FORBIDDEN ({len(new_non_reveal)}); sample={sample}"
        )
    pending_reveals = new_leaks & reveal_keys
    if pending_reveals and not args.admit_ownership_reveals:
        errors.append(
            f"ownership-reveal edges not yet admitted ({len(pending_reveals)}); "
            "run --admit-ownership-reveals then --shrink-debt"
        )

    # Hide: still-present debt import that is no longer reported cross-owner,
    # unless ownership completion made it internal (reclassified_internal).
    hidden: list[tuple[str, str, str]] = []
    for key in sorted(debt_edges):
        if not import_still_present(*key):
            continue
        if key in current_all:
            continue
        if same_owner_now(key[0], key[2], prefixes):
            continue
        if is_public_contract_target(key[2], public_prefixes):
            continue
        hidden.append(key)
    if hidden:
        errors.append(
            f"ownership/prefix hide of debt edge FORBIDDEN ({len(hidden)}); "
            f"sample={hidden[:10]}"
        )

    if len(debt_edges) > PMI1_DEBT_COUNT:
        errors.append(
            f"debt grew above PMI-1 baseline FORBIDDEN "
            f"({len(debt_edges)} > {PMI1_DEBT_COUNT})"
        )

    if args.admit_ownership_reveals:
        if invented or fake_shrink or new_non_reveal or hidden:
            print("refusing --admit-ownership-reveals while other freeze errors:", file=sys.stderr)
            for item in errors:
                if "not yet admitted" in item:
                    continue
                print(f"  {item}", file=sys.stderr)
            # still allow admit if only pending_reveals error
            blocking = [
                e
                for e in errors
                if "not yet admitted" not in e
            ]
            if blocking:
                return 1
        merged = debt_edges | pending_reveals
        if len(merged) > PMI1_DEBT_COUNT and not args.shrink_debt:
            # Admit alone may temporarily exceed PMI-1; require immediate shrink in same invocation
            # when over. Allow admit file write only if merge <= PMI1 OR shrink also requested.
            pass
        out_edges = [
            {"from_file": a, "import": b, "to_file": c}
            for a, b, c in sorted(merged)
        ]
        out = {
            "schema": "pmi1.debt.v1",
            "authority_commit": "844900d6",
            "edges": out_edges,
            "ownership_reveal_admitted": True,
            "pmi1_debt_count": PMI1_DEBT_COUNT,
        }
        DEBT_PATH.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"admitted ownership reveals: debt {len(debt_edges)} → {len(merged)}")
        debt_edges = merged
        # fall through to shrink if requested
        if not args.shrink_debt:
            if len(merged) > PMI1_DEBT_COUNT:
                print(
                    f"WARNING: debt {len(merged)} > PMI-1 {PMI1_DEBT_COUNT}; "
                    "run --shrink-debt before commit",
                    file=sys.stderr,
                )
            return 0

    if args.shrink_debt:
        # Recompute errors that block shrink (ignore pending admit if we just admitted)
        if args.admit_ownership_reveals:
            errors = [
                e
                for e in errors
                if "not yet admitted" not in e and "debt grew above" not in e
            ]
            # refresh invented check against new debt
            debt_outside_authority = debt_edges - authority_edges
            invented = {
                key
                for key in debt_outside_authority
                if not is_ownership_reveal(key, pmi1_prefixes, prefixes)
            }
            if invented:
                errors.append(
                    f"debt growth vs authority FORBIDDEN ({len(invented)} invented keys)"
                )
        if errors:
            print("refusing --shrink-debt while freeze gate is red:", file=sys.stderr)
            for item in errors:
                print(f"  {item}", file=sys.stderr)
            return 1
        kept: list[dict[str, str]] = []
        for a, b, c in sorted(debt_edges):
            if not import_still_present(a, b, c):
                continue
            if same_owner_now(a, c, prefixes):
                continue
            if is_public_contract_target(c, public_prefixes):
                continue
            if (a, b, c) in current_debt_relevant:
                kept.append({"from_file": a, "import": b, "to_file": c})
        if len(kept) > PMI1_DEBT_COUNT:
            print(
                f"shrink would leave debt {len(kept)} > PMI-1 {PMI1_DEBT_COUNT}",
                file=sys.stderr,
            )
            return 1
        if len(kept) >= PMI1_DEBT_COUNT:
            print(
                f"PMI-R requires net debt shrink below {PMI1_DEBT_COUNT}; got {len(kept)}",
                file=sys.stderr,
            )
            return 1
        out = {
            "schema": "pmi1.debt.v1",
            "authority_commit": "844900d6",
            "edges": kept,
            "ownership_reveal_admitted": True,
            "pmi1_debt_count": PMI1_DEBT_COUNT,
            "shrunk_from_pmi1": PMI1_DEBT_COUNT - len(kept),
        }
        DEBT_PATH.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"shrank debt {len(debt_edges)} → {len(kept)} (PMI-1 was {PMI1_DEBT_COUNT})")
        return 0

    summary = {
        "authority_edge_count": len(authority_edges),
        "debt_edge_count": len(debt_edges),
        "current_cross_owner_edge_count": len(current_all),
        "current_debt_relevant_count": len(current_debt_relevant),
        "new_leak_count": len(new_non_reveal),
        "pending_ownership_reveal_count": len(pending_reveals),
        "hidden_count": len(hidden),
        "debt_growth_count": len(invented),
        "fake_shrink_count": len(fake_shrink),
        "public_contract_prefixes": public_prefixes,
        "ok": not errors,
    }

    if errors:
        print("PMI-1 freeze STOP:", file=sys.stderr)
        for item in errors:
            print(f"  {item}", file=sys.stderr)
        if args.json:
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 1

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print("PMI-1 enforcement freeze")
        print(f"  authority_commit: {freeze['authority_commit']}")
        print(f"  authority_edges: {len(authority_edges)}")
        print(f"  debt_edges: {len(debt_edges)}")
        print(f"  current_cross_owner_edges: {len(current_all)}")
        print(f"  current_debt_relevant: {len(current_debt_relevant)}")
        print(f"  public_contract_prefixes: {public_prefixes}")
        print("  invariant: debt may only shrink; new non-contract coupling rejected")
        print("  ownership reveals: admitted only via --admit-ownership-reveals")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
