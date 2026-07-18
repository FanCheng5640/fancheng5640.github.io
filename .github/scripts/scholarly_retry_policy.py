"""Choose whether a scheduled scholarly sync should run or quietly retry later."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from scholarly_freshness import google_scholar_current_for_today


SCHEDULE_ATTEMPTS = {
    "30 7 * * *": 1,
    "30 8 * * *": 2,
    "30 9 * * *": 3,
}
TOTAL_ATTEMPTS = len(SCHEDULE_ATTEMPTS)


@dataclass(frozen=True)
class RetryDecision:
    attempt_number: int
    total_attempts: int
    final_attempt: bool
    already_current: bool
    should_sync: bool
    reason: str


def load_google_scholar(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    data["exists"] = True
    return data


def decide_retry_policy(
    *,
    event_name: str,
    schedule: str,
    scholar_data_path: Path,
    now: datetime | None = None,
) -> RetryDecision:
    if event_name != "schedule":
        return RetryDecision(
            attempt_number=TOTAL_ATTEMPTS,
            total_attempts=TOTAL_ATTEMPTS,
            final_attempt=True,
            already_current=False,
            should_sync=True,
            reason=f"Manual event {event_name or 'unknown'} runs immediately.",
        )

    if schedule not in SCHEDULE_ATTEMPTS:
        raise ValueError(f"Unsupported scholarly sync schedule: {schedule!r}")

    attempt_number = SCHEDULE_ATTEMPTS[schedule]
    final_attempt = attempt_number == TOTAL_ATTEMPTS
    scholar_data = load_google_scholar(scholar_data_path)
    already_current = google_scholar_current_for_today(scholar_data, now=now)
    should_sync = attempt_number == 1 or not already_current

    if attempt_number == 1:
        reason = "Primary daily scholarly sync attempt."
    elif already_current:
        reason = "Google Scholar data is already current for today; retry is unnecessary."
    else:
        reason = f"Google Scholar data is stale; running retry {attempt_number}/{TOTAL_ATTEMPTS}."

    return RetryDecision(
        attempt_number=attempt_number,
        total_attempts=TOTAL_ATTEMPTS,
        final_attempt=final_attempt,
        already_current=already_current,
        should_sync=should_sync,
        reason=reason,
    )


def write_github_output(decision: RetryDecision, output_path: str) -> None:
    if not output_path:
        return
    values = asdict(decision)
    with Path(output_path).open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            if isinstance(value, bool):
                value = "true" if value else "false"
            handle.write(f"{key}={value}\n")


def parse_now(value: str) -> datetime | None:
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("--now must include timezone information")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event-name", default=os.environ.get("GITHUB_EVENT_NAME", ""))
    parser.add_argument("--schedule", default=os.environ.get("GITHUB_EVENT_SCHEDULE", ""))
    parser.add_argument("--scholar-data", default="_data/google_scholar.json")
    parser.add_argument("--now", default="", help="Timezone-aware ISO timestamp for deterministic tests.")
    parser.add_argument("--github-output", default=os.environ.get("GITHUB_OUTPUT", ""))
    args = parser.parse_args()

    decision = decide_retry_policy(
        event_name=args.event_name,
        schedule=args.schedule,
        scholar_data_path=Path(args.scholar_data),
        now=parse_now(args.now),
    )
    write_github_output(decision, args.github_output)
    print(json.dumps(asdict(decision), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
