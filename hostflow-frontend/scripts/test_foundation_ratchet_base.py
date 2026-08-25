#!/usr/bin/env python3
"""Contract tests for Foundation ratchet comparison-base (no git required)."""

from __future__ import annotations

import unittest

from foundation_ratchet_base import (
    TRUSTED_INTEGRATION_REF,
    RatchetContext,
    context_from_env,
    decide_ratchet,
)

ZERO = "0" * 40
BEFORE = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
AFTER = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


class DecideRatchetTests(unittest.TestCase):
    def test_pr_into_integration_uses_merge_base_of_base_and_head(self) -> None:
        decision = decide_ratchet(
            RatchetContext(
                event_name="pull_request",
                pr_base_ref="integration/release-product-a-b",
                pr_head_ref="feat/overlay",
                pr_same_repo=True,
            )
        )
        self.assertEqual(decision.action, "diff")
        self.assertEqual(decision.mode, "pull-request")
        self.assertTrue(decision.triple_dot)
        self.assertEqual(
            decision.spec,
            "origin/integration/release-product-a-b...HEAD",
        )

    def test_promote_integration_to_main_is_already_ratcheted(self) -> None:
        decision = decide_ratchet(
            RatchetContext(
                event_name="pull_request",
                pr_base_ref="main",
                pr_head_ref="integration/release-product-a-b",
                pr_same_repo=True,
            )
        )
        self.assertEqual(decision.action, "skip")
        self.assertEqual(decision.mode, "already-ratcheted")
        self.assertEqual(decision.spec, "")

    def test_fork_named_like_integration_is_not_skipped(self) -> None:
        decision = decide_ratchet(
            RatchetContext(
                event_name="pull_request",
                pr_base_ref="main",
                pr_head_ref="integration/release-product-a-b",
                pr_same_repo=False,
            )
        )
        self.assertEqual(decision.action, "diff")
        self.assertEqual(decision.spec, "origin/main...HEAD")

    def test_pr_missing_base_fails_closed(self) -> None:
        decision = decide_ratchet(RatchetContext(event_name="pull_request"))
        self.assertEqual(decision.action, "fail")
        self.assertEqual(decision.mode, "pr-missing-base")
        self.assertEqual(decision.spec, "")

    def test_push_uses_before_after_range_not_main(self) -> None:
        decision = decide_ratchet(
            RatchetContext(
                event_name="push",
                push_before=BEFORE,
                push_after=AFTER,
            )
        )
        self.assertEqual(decision.action, "diff")
        self.assertEqual(decision.mode, "push-range")
        self.assertFalse(decision.triple_dot)
        self.assertEqual(decision.spec, f"{BEFORE}..{AFTER}")
        self.assertNotIn("main", decision.spec)

    def test_push_to_main_still_uses_before_after(self) -> None:
        decision = decide_ratchet(
            RatchetContext(
                event_name="push",
                push_before=BEFORE,
                push_after=AFTER,
                ref_name="main",
            )
        )
        self.assertEqual(decision.spec, f"{BEFORE}..{AFTER}")

    def test_first_push_compares_trusted_integration_not_head_minus_one(self) -> None:
        decision = decide_ratchet(
            RatchetContext(
                event_name="push",
                push_before=ZERO,
                push_after=AFTER,
                ref_name="feat/new-branch",
            )
        )
        self.assertEqual(decision.action, "diff")
        self.assertEqual(decision.mode, "push-first-ref")
        self.assertTrue(decision.triple_dot)
        self.assertEqual(decision.spec, f"{TRUSTED_INTEGRATION_REF}...{AFTER}")
        self.assertNotIn("HEAD~1", decision.spec)
        self.assertNotIn("main", decision.spec)

    def test_push_missing_before_fails_closed(self) -> None:
        decision = decide_ratchet(
            RatchetContext(event_name="push", push_after=AFTER)
        )
        self.assertEqual(decision.action, "fail")
        self.assertEqual(decision.mode, "push-missing-before")

    def test_push_deleted_ref_skips(self) -> None:
        decision = decide_ratchet(
            RatchetContext(event_name="push", push_before=BEFORE, push_after=ZERO)
        )
        self.assertEqual(decision.action, "skip")
        self.assertEqual(decision.mode, "ref-deleted")

    def test_force_push_keeps_before_after_and_does_not_skip(self) -> None:
        decision = decide_ratchet(
            RatchetContext(
                event_name="push",
                push_before=BEFORE,
                push_after=AFTER,
                push_forced=True,
            )
        )
        self.assertEqual(decision.action, "diff")
        self.assertEqual(decision.mode, "push-force")
        self.assertEqual(decision.spec, f"{BEFORE}..{AFTER}")

    def test_override_wins_over_promote_skip(self) -> None:
        decision = decide_ratchet(
            RatchetContext(
                event_name="pull_request",
                pr_base_ref="main",
                pr_head_ref="integration/release-product-a-b",
                pr_same_repo=True,
                override_base="origin/main",
            )
        )
        self.assertEqual(decision.action, "diff")
        self.assertEqual(decision.mode, "override")
        self.assertEqual(decision.spec, "origin/main...HEAD")

    def test_override_zero_sha_fails_closed(self) -> None:
        decision = decide_ratchet(RatchetContext(override_base=ZERO))
        self.assertEqual(decision.action, "fail")
        self.assertEqual(decision.mode, "override-zero")

    def test_local_uses_trusted_integration_not_main(self) -> None:
        decision = decide_ratchet(RatchetContext())
        self.assertEqual(decision.action, "diff")
        self.assertEqual(decision.mode, "local-trusted")
        self.assertEqual(decision.spec, f"{TRUSTED_INTEGRATION_REF}...HEAD")

    def test_unknown_event_fails_closed(self) -> None:
        decision = decide_ratchet(RatchetContext(event_name="workflow_dispatch"))
        self.assertEqual(decision.action, "fail")
        self.assertEqual(decision.mode, "unknown-event")

    def test_context_from_env_reads_github_fallbacks(self) -> None:
        ctx = context_from_env(
            {
                "GITHUB_EVENT_NAME": "pull_request",
                "GITHUB_BASE_REF": "integration/release-product-a-b",
                "GITHUB_HEAD_REF": "feat/x",
                "FOUNDATION_PR_SAME_REPO": "true",
            }
        )
        decision = decide_ratchet(ctx)
        self.assertEqual(
            decision.spec, "origin/integration/release-product-a-b...HEAD"
        )


if __name__ == "__main__":
    unittest.main()
