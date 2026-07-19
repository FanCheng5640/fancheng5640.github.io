from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / ".github" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from scholarly_retry_policy import decide_retry_policy  # noqa: E402


class ScholarlyRetryPolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.scholar_path = Path(self.temp_dir.name) / "google_scholar.json"
        self.now = datetime(2026, 7, 18, 5, 30, tzinfo=timezone.utc)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_status(self, updated: str, sync_status: str = "ok") -> None:
        self.scholar_path.write_text(
            json.dumps({"updated": updated, "sync_status": sync_status}),
            encoding="utf-8",
        )

    def decide(self, schedule: str, event_name: str = "schedule"):
        return decide_retry_policy(
            event_name=event_name,
            schedule=schedule,
            scholar_data_path=self.scholar_path,
            now=self.now,
        )

    def test_primary_attempt_always_runs_even_if_already_current(self) -> None:
        self.write_status("2026-07-18")
        decision = self.decide("15 6 * * *")
        self.assertTrue(decision.should_sync)
        self.assertTrue(decision.already_current)
        self.assertFalse(decision.final_attempt)

    def test_second_attempt_skips_when_primary_succeeded(self) -> None:
        self.write_status("2026-07-18")
        decision = self.decide("45 6 * * *")
        self.assertFalse(decision.should_sync)
        self.assertFalse(decision.final_attempt)

    def test_second_attempt_runs_when_primary_failed(self) -> None:
        self.write_status("2026-07-17")
        decision = self.decide("45 6 * * *")
        self.assertTrue(decision.should_sync)
        self.assertFalse(decision.final_attempt)

    def test_third_attempt_still_finishes_before_the_workday(self) -> None:
        self.write_status("2026-07-17")
        decision = self.decide("15 7 * * *")
        self.assertTrue(decision.should_sync)
        self.assertFalse(decision.final_attempt)

    def test_final_attempt_runs_and_can_raise_the_daily_alert(self) -> None:
        self.write_status("2026-07-17")
        decision = self.decide("5 9 * * *")
        self.assertTrue(decision.should_sync)
        self.assertTrue(decision.final_attempt)

    def test_failed_status_is_not_treated_as_current(self) -> None:
        self.write_status("2026-07-18", sync_status="stale")
        self.assertTrue(self.decide("45 6 * * *").should_sync)

    def test_missing_data_runs_a_retry(self) -> None:
        self.assertTrue(self.decide("45 6 * * *").should_sync)

    def test_manual_run_is_immediate_and_final(self) -> None:
        self.write_status("2026-07-18")
        decision = self.decide("", event_name="workflow_dispatch")
        self.assertTrue(decision.should_sync)
        self.assertTrue(decision.final_attempt)

    def test_israel_date_is_used_across_utc_midnight(self) -> None:
        self.now = datetime(2026, 1, 10, 23, 30, tzinfo=timezone.utc)
        self.write_status("2026-01-11")
        self.assertFalse(self.decide("45 6 * * *").should_sync)

    def test_unknown_schedule_fails_visibly(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported scholarly sync schedule"):
            self.decide("15 8 * * *")

    def test_workflow_contract_has_prework_retries_and_final_only_alert(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "sync_orcid_publications.yml").read_text(
            encoding="utf-8"
        )
        for schedule in ("15 6", "45 6", "15 7", "5 9"):
            self.assertIn(f'cron: "{schedule} * * *"', workflow)
        self.assertEqual(workflow.count('timezone: "Asia/Jerusalem"'), 4)
        self.assertIn("steps.retry_policy.outputs.should_sync == 'true'", workflow)
        self.assertIn("steps.retry_policy.outputs.final_attempt == 'true'", workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow)

    def test_local_sync_uses_an_isolated_worktree_when_main_tree_is_dirty(self) -> None:
        script = (REPO_ROOT / "scripts" / "local_google_scholar_auto_sync.ps1").read_text(
            encoding="utf-8-sig"
        )
        self.assertIn('worktree", "add", "--detach"', script)
        self.assertIn('worktree", "remove", "--force"', script)
        self.assertNotIn("Worktree is not clean before sync", script)


if __name__ == "__main__":
    unittest.main()
