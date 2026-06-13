"""Sync public Google Scholar citation metrics into Jekyll data."""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


PROFILE_URL = "https://scholar.google.com/citations?user=cXkaM-MAAAAJ&hl=en"
OUTPUT_PATH = Path("_data/google_scholar.json")
USER_AGENT = "Mozilla/5.0 fancheng5640.github.io citation sync"


def fetch_profile_html() -> str:
    request = urllib.request.Request(
        PROFILE_URL,
        headers={"User-Agent": USER_AGENT},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_metrics(page: str) -> dict:
    metric_labels = {
        "Citations": "citations",
        "h-index": "h_index",
        "i10-index": "i10_index",
    }
    metrics = {}
    rows = re.findall(
        r'<tr><td class="gsc_rsb_sc1"><a[^>]*>(.*?)</a></td>'
        r'<td class="gsc_rsb_std">(.*?)</td><td class="gsc_rsb_std">(.*?)</td></tr>',
        page,
        flags=re.S,
    )
    for label, all_value, recent_value in rows:
        key = metric_labels.get(html.unescape(re.sub(r"<.*?>", "", label)).strip())
        if not key:
            continue
        metrics[key] = {
            "all": int(re.sub(r"\D", "", all_value) or 0),
            "recent": int(re.sub(r"\D", "", recent_value) or 0),
        }
    required = {"citations", "h_index", "i10_index"}
    missing = required - set(metrics)
    if missing:
        raise ValueError(f"Missing Google Scholar metrics: {sorted(missing)}")
    return metrics


def parse_yearly_citations(page: str) -> list[dict]:
    year_positions = [
        (int(position), int(year))
        for position, year in re.findall(
            r'<span class="gsc_g_t" style="right:(\d+)px">(\d{4})</span>',
            page,
        )
    ]
    bars = [
        (int(position), int(value))
        for position, value in re.findall(
            r'<a href="javascript:void\(0\)" class="gsc_g_a" style="right:(\d+)px;[^"]*">'
            r'<span class="gsc_g_al">(\d+)</span></a>',
            page,
        )
    ]
    if not year_positions:
        raise ValueError("Missing Google Scholar yearly citation axis")

    values_by_year = {year: 0 for _, year in year_positions}
    for bar_position, value in bars:
        nearest_position, nearest_year = min(
            year_positions, key=lambda item: abs(item[0] - bar_position)
        )
        if abs(nearest_position - bar_position) > 12:
            raise ValueError(
                f"Could not map citation bar at {bar_position}px to a year axis tick"
            )
        values_by_year[nearest_year] = value

    return [
        {"year": year, "citations": values_by_year[year]}
        for _, year in sorted(year_positions, key=lambda item: item[1])
    ]


def summary_title(points: list[dict]) -> str:
    return "Google Scholar citations"


def main() -> int:
    page = fetch_profile_html()
    data = {
        "profile_url": PROFILE_URL,
        "source": "Google Scholar",
        "updated": datetime.now(timezone.utc).date().isoformat(),
        "summary_title": summary_title(parse_yearly_citations(page)),
        "metrics": parse_metrics(page),
        "citations_by_year": parse_yearly_citations(page),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Synced Google Scholar metrics into {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: Google Scholar sync failed: {exc}", file=sys.stderr)
        raise
