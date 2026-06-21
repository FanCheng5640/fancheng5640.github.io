"""Validate Journal Impact Factor data freshness and consistency.

The site displays Journal Impact Factor values from ``_data/journal_metrics.json``.
This check keeps the public data, release wording, and publication front matter
aligned, and it fails after the annual JCR release window if the metric year is
stale.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date
from pathlib import Path


METRICS_PATH = Path("_data/journal_metrics.json")
PUBLICATIONS_DIR = Path("_publications")
JCR_EXPECTED_FROM_MONTH_DAY = (6, 15)


def expected_metric_year(today: date | None = None) -> int:
    """Return the JCR metric year expected for the current date."""
    today = today or date.today()
    if (today.month, today.day) >= JCR_EXPECTED_FROM_MONTH_DAY:
        return today.year - 1
    return today.year - 2


def front_matter(markdown: str) -> str:
    if not markdown.startswith("---\n"):
        return ""
    end = markdown.find("\n---", 4)
    if end == -1:
        return ""
    return markdown[4:end]


def field(front_matter_text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.*?)\s*$", front_matter_text, re.M)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")


def as_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_metrics() -> tuple[dict, dict[str, dict]]:
    if not METRICS_PATH.exists():
        raise FileNotFoundError(f"Missing {METRICS_PATH}")
    data = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
    metadata = data.get("metadata", {})
    journals = {}
    for journal in data.get("journals", []):
        name = str(journal.get("name", "")).strip()
        if name:
            journals[name] = journal
    return metadata, journals


def validate() -> list[str]:
    errors: list[str] = []
    metadata, journals = load_metrics()
    metric_year = int(metadata.get("metric_year") or 0)
    expected_year = expected_metric_year()
    if metric_year < expected_year:
        errors.append(
            f"{METRICS_PATH} metric_year={metric_year} is stale; "
            f"expected at least {expected_year} after the annual JCR release window."
        )

    if not str(metadata.get("release_note_url", "")).startswith("https://"):
        errors.append("metadata.release_note_url must be an https URL.")

    release_label = str(metadata.get("release_label", "")).strip()
    expected_release_year = str(metric_year + 1)
    if (
        expected_release_year not in release_label
        or "Journal Citation Reports" not in release_label
    ):
        errors.append(
            "metadata.release_label must name the release version, e.g. "
            f"'{expected_release_year} Journal Citation Reports'."
        )

    for name, journal in journals.items():
        if as_float(journal.get("impact_factor")) <= 0:
            errors.append(f"{name}: impact_factor must be positive.")
        if not str(journal.get("source", "")).startswith("https://"):
            errors.append(f"{name}: source must be an https URL.")

    for path in sorted(PUBLICATIONS_DIR.glob("*.md")):
        fm = front_matter(path.read_text(encoding="utf-8"))
        venue = field(fm, "venue")
        if not venue or venue not in journals:
            continue
        journal = journals[venue]
        publication_if = as_float(field(fm, "journal_impact_factor"))
        canonical_if = as_float(journal.get("impact_factor"))
        if abs(publication_if - canonical_if) > 0.0001:
            errors.append(
                f"{path}: journal_impact_factor={publication_if:g} does not match "
                f"{venue} canonical value {canonical_if:g}."
            )
        publication_year = field(fm, "impact_factor_year")
        if publication_year and publication_year != str(metric_year):
            errors.append(
                f"{path}: impact_factor_year={publication_year} does not match "
                f"metadata metric_year={metric_year}."
            )
        publication_source = field(fm, "impact_factor_source")
        if publication_source and publication_source != str(journal.get("source", "")):
            errors.append(
                f"{path}: impact_factor_source does not match {venue} canonical source."
            )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("Journal metric validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print("Journal metric validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
