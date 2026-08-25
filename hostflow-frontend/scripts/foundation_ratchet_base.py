"""Foundation ratchet comparison-base contract.

The blocking check answers: did THIS change introduce new deprecated tokens?
It is not a migration scanner. Full-tree debt is `foundation:scan` (non-blocking).

Do not fall back to `origin/main` for push or local runs. That mismatch reclassifies
already-ratcheted integration history as "new" tokens (ratchet base mismatch).
Unresolved ranges fail closed — never skip into a false green.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import os

TRUSTED_INTEGRATION_REF = "origin/integration/release-product-a-b"
PROMOTE_HEAD_REF = "integration/release-product-a-b"
PROMOTE_BASE_REF = "main"


def is_zero_sha(value: str | None) -> bool:
    text = (value or "").strip()
    return bool(text) and set(text) <= {"0"}


def is_present_sha(value: str | None) -> bool:
    text = (value or "").strip()
    return bool(text) and not is_zero_sha(text)


def env_truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RatchetContext:
    event_name: str = ""
    pr_base_ref: str = ""
    pr_head_ref: str = ""
    pr_same_repo: bool = False
    push_before: str = ""
    push_after: str = ""
    push_forced: bool = False
    ref_name: str = ""
    override_base: str = ""
    trusted_integration_ref: str = TRUSTED_INTEGRATION_REF


@dataclass(frozen=True)
class RatchetDecision:
    action: str  # "diff" | "skip" | "fail"
    from_ref: str = ""
    to_ref: str = "HEAD"
    triple_dot: bool = False
    mode: str = ""
    reason: str = ""

    @property
    def spec(self) -> str:
        if self.action != "diff":
            return ""
        sep = "..." if self.triple_dot else ".."
        return f"{self.from_ref}{sep}{self.to_ref}"


def context_from_env(env: Mapping[str, str] | None = None) -> RatchetContext:
    source = os.environ if env is None else env
    return RatchetContext(
        event_name=(
            source.get("FOUNDATION_EVENT_NAME") or source.get("GITHUB_EVENT_NAME") or ""
        ).strip(),
        pr_base_ref=(
            source.get("FOUNDATION_PR_BASE_REF") or source.get("GITHUB_BASE_REF") or ""
        ).strip(),
        pr_head_ref=(
            source.get("FOUNDATION_PR_HEAD_REF") or source.get("GITHUB_HEAD_REF") or ""
        ).strip(),
        pr_same_repo=env_truthy(source.get("FOUNDATION_PR_SAME_REPO")),
        push_before=(source.get("FOUNDATION_PUSH_BEFORE") or "").strip(),
        push_after=(source.get("FOUNDATION_PUSH_AFTER") or "").strip(),
        push_forced=env_truthy(source.get("FOUNDATION_PUSH_FORCED")),
        ref_name=(
            source.get("FOUNDATION_REF_NAME") or source.get("GITHUB_REF_NAME") or ""
        ).strip(),
        override_base=(source.get("FOUNDATION_DIFF_BASE") or "").strip(),
    )


def decide_ratchet(ctx: RatchetContext) -> RatchetDecision:
    if ctx.override_base:
        if is_zero_sha(ctx.override_base):
            return RatchetDecision(
                action="fail",
                mode="override-zero",
                reason=(
                    "FOUNDATION_DIFF_BASE is a zero SHA; refusing to skip "
                    "(fail-closed)."
                ),
            )
        return RatchetDecision(
            action="diff",
            from_ref=ctx.override_base,
            to_ref="HEAD",
            triple_dot=True,
            mode="override",
            reason=f"explicit FOUNDATION_DIFF_BASE={ctx.override_base}",
        )

    event = ctx.event_name.strip().lower()
    if event == "pull_request":
        return _decide_pull_request(ctx)
    if event == "push":
        return _decide_push(ctx)
    if event:
        return RatchetDecision(
            action="fail",
            mode="unknown-event",
            reason=(
                f"unknown event {event!r}; refusing to guess a comparison base "
                "(fail-closed)."
            ),
        )
    return RatchetDecision(
        action="diff",
        from_ref=ctx.trusted_integration_ref,
        to_ref="HEAD",
        triple_dot=True,
        mode="local-trusted",
        reason=(
            "no CI event; compare merge-base(trusted integration, HEAD)..HEAD"
        ),
    )


def _decide_pull_request(ctx: RatchetContext) -> RatchetDecision:
    base = ctx.pr_base_ref.strip()
    head = ctx.pr_head_ref.strip()
    if (
        ctx.pr_same_repo
        and base == PROMOTE_BASE_REF
        and head == PROMOTE_HEAD_REF
    ):
        return RatchetDecision(
            action="skip",
            mode="already-ratcheted",
            reason=(
                "promote PR integration/release-product-a-b → main: contents "
                "already passed the Foundation ratchet at integration entry"
            ),
        )
    if not base:
        return RatchetDecision(
            action="fail",
            mode="pr-missing-base",
            reason=(
                "pull_request without base ref; refusing to fall back to main "
                "(fail-closed)."
            ),
        )
    return RatchetDecision(
        action="diff",
        from_ref=f"origin/{base}",
        to_ref="HEAD",
        triple_dot=True,
        mode="pull-request",
        reason=f"PR vs merge-base(origin/{base}, HEAD)..HEAD",
    )


def _decide_push(ctx: RatchetContext) -> RatchetDecision:
    before = ctx.push_before.strip()
    after = ctx.push_after.strip()

    if is_zero_sha(after):
        return RatchetDecision(
            action="skip",
            mode="ref-deleted",
            reason="push deletes the ref; no tip to ratchet",
        )

    to_ref = after if is_present_sha(after) else "HEAD"

    if before == "":
        return RatchetDecision(
            action="fail",
            mode="push-missing-before",
            reason=(
                "push event missing github.event.before; refusing to fall back "
                "to main or HEAD~1 (fail-closed)."
            ),
        )

    if is_zero_sha(before):
        return RatchetDecision(
            action="diff",
            from_ref=ctx.trusted_integration_ref,
            to_ref=to_ref,
            triple_dot=True,
            mode="push-first-ref",
            reason=(
                "first push (zero before SHA): compare merge-base(trusted "
                "integration, tip)..tip — not HEAD~1, not main"
            ),
        )

    mode = "push-force" if ctx.push_forced else "push-range"
    reason = (
        f"force-push range {before}..{to_ref}; unresolved SHA must fail-closed"
        if ctx.push_forced
        else f"push range {before}..{to_ref}"
    )
    return RatchetDecision(
        action="diff",
        from_ref=before,
        to_ref=to_ref,
        triple_dot=False,
        mode=mode,
        reason=reason,
    )
