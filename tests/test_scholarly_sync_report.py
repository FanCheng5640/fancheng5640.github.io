from __future__ import annotations

import os
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / ".github" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import scholarly_sync_report  # noqa: E402


class ScholarlySyncReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 7, 24, 7, 5, tzinfo=timezone.utc)

    def build_cache_report(self, updated: str) -> dict:
        before = {
            "publications": {},
            "statistics": {},
            "news": {"hash": "same"},
            "google_scholar": {
                "exists": True,
                "updated": updated,
                "sync_status": "ok",
                "metrics": {},
                "citations_by_year": [],
                "publication_citations": {},
            },
        }
        after = dict(before)
        scholar_status = {
            "status": "cached",
            "used_cache": True,
            "provider": "google_scholar_html",
            "error": "HTTP Error 429",
            "committed_stale_status": False,
        }
        with patch.object(scholarly_sync_report, "datetime") as fake_datetime:
            fake_datetime.now.return_value = self.now
            fake_datetime.fromisoformat = datetime.fromisoformat
            return scholarly_sync_report.build_report(before, after, scholar_status)[1]

    def test_default_report_is_strict_for_manual_runs(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            metadata = self.build_cache_report("2026-07-23")

        self.assertTrue(metadata["google_scholar_sync_alert"])
        self.assertFalse(metadata["google_scholar_recent_enough"])
        self.assertEqual(metadata["google_scholar_recent_max_age_days"], 0)

    def test_scheduled_report_tolerates_short_shutdown_gap(self) -> None:
        with patch.dict(os.environ, {"GOOGLE_SCHOLAR_RECENT_MAX_AGE_DAYS": "2"}, clear=True):
            metadata = self.build_cache_report("2026-07-23")

        self.assertFalse(metadata["google_scholar_sync_alert"])
        self.assertTrue(metadata["google_scholar_recent_enough"])
        self.assertEqual(metadata["google_scholar_recent_max_age_days"], 2)

    def test_scheduled_report_still_alerts_after_multi_day_gap(self) -> None:
        with patch.dict(os.environ, {"GOOGLE_SCHOLAR_RECENT_MAX_AGE_DAYS": "2"}, clear=True):
            metadata = self.build_cache_report("2026-07-21")

        self.assertTrue(metadata["google_scholar_sync_alert"])
        self.assertFalse(metadata["google_scholar_recent_enough"])

    def test_workflow_uses_shutdown_grace_only_for_scheduled_runs(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "sync_orcid_publications.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("GOOGLE_SCHOLAR_RECENT_MAX_AGE_DAYS", workflow)
        self.assertIn("github.event_name == 'schedule' && '2' || '0'", workflow)


if __name__ == "__main__":
    unittest.main()
