from __future__ import annotations

import json
from typing import Any, Dict, Optional, Set

# ---------- I/O ----------


def load_ruleset(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- helpers ----------


def _get_ctx_value(ctx: Dict[str, Any], dotted_key: str) -> Any:
    """Достаёт значение по ключу с точками: 'vacancy.requires_driver_attestation'."""
    cur: Any = ctx
    for part in dotted_key.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _matches(when: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
    """Проверка условий: если значение-список → ctx in list, иначе точное совпадение."""
    for key, expected in when.items():
        val = _get_ctx_value(ctx, key)
        if isinstance(expected, list):
            if val not in expected:
                return False
        else:
            if val != expected:
                return False
    return True


def _is_simple_schema(ruleset: Dict[str, Any]) -> bool:
    """
    Простая схема: корневые поля 'required', 'optional', 'expiring_soon_days'.
    Расширенная — содержит 'candidate'/'vacancy'.
    """
    return (
        isinstance(ruleset, dict)
        and ("required" in ruleset or "optional" in ruleset)
        and "candidate" not in ruleset
        and "vacancy" not in ruleset
    )


# ---------- public API ----------


def compute_candidate_checklist(
    ctx: Dict[str, Any], ruleset: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Возвращает итоговый чек-лист по кандидату.

    Поддерживает 2 варианта ruleset:
      1) Простая схема:
         {"required":[...], "optional":[...], "expiring_soon_days":30}
      2) Расширенная схема (candidate/defaults/overrides, vacancy/category_sets/additions, validity).
    """
    if _is_simple_schema(ruleset):
        # ПРИВОДИМ К set[str]
        required_set: Set[str] = {str(x) for x in ruleset.get("required", [])}
        optional_set: Set[str] = {str(x) for x in ruleset.get("optional", [])}
        return {
            "requiredTypes": sorted(required_set),
            "optionalTypes": sorted(optional_set),
            "debug": {
                "schema": "simple",
                "added_by_overrides": [],
                "removed_by_overrides": [],
                "added_by_category": [],
                "added_by_vacancy": [],
            },
        }

    # ---- Расширенная схема ----
    rs_cand = ruleset.get("candidate", {}) or {}
    defaults = rs_cand.get("defaults", {}) or {}

    # ВАЖНО: именно set[str], не list
    required: Set[str] = {str(x) for x in defaults.get("requiredTypes", [])}
    optional: Set[str] = {str(x) for x in defaults.get("optionalTypes", [])}

    added_by_overrides: Set[str] = set()
    removed_by_overrides: Set[str] = set()
    added_by_category: Set[str] = set()
    added_by_vacancy: Set[str] = set()

    # 1) candidate.overrides
    for rule in rs_cand.get("overrides", []) or []:
        when = rule.get("when", {}) or {}
        if _matches(when, ctx):
            for t in rule.get("require", []) or []:
                t = str(t)
                if t not in required:
                    required.add(t)
                    added_by_overrides.add(t)
                optional.discard(t)
            for t in rule.get("remove", []) or []:
                t = str(t)
                if t in required:
                    required.discard(t)
                    removed_by_overrides.add(t)
                optional.discard(t)

    # 2) vacancy.category_sets
    vacancy_rules = ruleset.get("vacancy", {}) or {}
    category_sets = vacancy_rules.get("category_sets", {}) or {}
    category: Optional[str] = None
    if isinstance(ctx.get("vacancy"), dict):
        category = ctx["vacancy"].get("category")

    if isinstance(category, str) and category in category_sets:
        cat = category_sets.get(category) or {}
        for t in cat.get("requiredTypes", []) or []:
            t = str(t)
            if t not in required:
                required.add(t)
                added_by_category.add(t)
            optional.discard(t)
        for t in cat.get("optionalTypes", []) or []:
            t = str(t)
            if t not in required:
                optional.add(t)

    # 3) vacancy.additions
    additions = vacancy_rules.get("additions", []) or []
    for rule in additions:
        when = rule.get("when", {}) or {}
        if _matches(when, ctx):
            for t in rule.get("require", []) or []:
                t = str(t)
                if t not in required:
                    required.add(t)
                    added_by_vacancy.add(t)
                optional.discard(t)

    return {
        "requiredTypes": sorted(required),
        "optionalTypes": sorted(optional),
        "debug": {
            "schema": "advanced",
            "added_by_overrides": sorted(added_by_overrides),
            "removed_by_overrides": sorted(removed_by_overrides),
            "added_by_category": sorted(added_by_category),
            "added_by_vacancy": sorted(added_by_vacancy),
        },
    }


def expiring_threshold_for(doc_type: str, ruleset: Dict[str, Any]) -> int:
    """
    Возвращает порог «скоро истекает» в днях для doc_type.
    Для простой схемы — 'expiring_soon_days'.
    Для расширенной — validity[doc_type].expiring_soon_days, иначе expiring_soon_default_days (или 30).
    """
    if _is_simple_schema(ruleset):
        return int(ruleset.get("expiring_soon_days", 30))

    per_type = (ruleset.get("validity", {}) or {}).get(doc_type, {}) or {}
    if "expiring_soon_days" in per_type:
        return int(per_type["expiring_soon_days"])
    return int(ruleset.get("expiring_soon_default_days", 30))
