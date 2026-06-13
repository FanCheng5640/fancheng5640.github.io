"""Sync public Google Scholar citation metrics into Jekyll data."""

from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin


PROFILE_URL = "https://scholar.google.com/citations?user=cXkaM-MAAAAJ&hl=en"
OUTPUT_PATH = Path("_data/google_scholar.json")
PUBLICATIONS_DIR = Path("_publications")
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


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<\?\s*TeX\\break\s*\?>", " ", value, flags=re.I)
    value = re.sub(r"<.*?>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def normalize_title(value: str) -> str:
    value = clean_text(value).lower()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_publication_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\s*\n(.*?)\n---", text, flags=re.S)
    if not match:
        raise ValueError(f"Missing front matter in {path}")

    front_matter = match.group(1)
    fields = {}
    for key in ("title", "doi"):
        field_match = re.search(rf'^{key}:\s*["\']?(.*?)["\']?\s*$', front_matter, flags=re.M)
        fields[key] = clean_text(field_match.group(1)) if field_match else ""

    if not fields["title"]:
        raise ValueError(f"Missing publication title in {path}")
    return {
        "path": path.as_posix(),
        "title": fields["title"],
        "normalized_title": normalize_title(fields["title"]),
        "doi": fields["doi"],
    }


def load_local_publications() -> list[dict]:
    if not PUBLICATIONS_DIR.exists():
        raise ValueError(f"Missing publications directory: {PUBLICATIONS_DIR}")

    publications = [
        parse_publication_front_matter(path)
        for path in sorted(PUBLICATIONS_DIR.glob("*.md"))
    ]
    if not publications:
        raise ValueError("No local publications found")
    return publications


def parse_scholar_publications(page: str) -> list[dict]:
    rows = re.findall(r'<tr class="gsc_a_tr">(.*?)</tr>', page, flags=re.S)
    if not rows:
        raise ValueError("Missing Google Scholar publication table")

    publications = []
    for row in rows:
        title_match = re.search(
            r'<a href="([^"]*)" class="gsc_a_at">(.*?)</a>',
            row,
            flags=re.S,
        )
        if not title_match:
            continue

        cites_match = re.search(
            r'<td class="gsc_a_c"><a href="([^"]*)" class="gsc_a_ac[^"]*">(.*?)</a></td>',
            row,
            flags=re.S,
        )
        cites_text = clean_text(cites_match.group(2)) if cites_match else ""
        citations_url = html.unescape(cites_match.group(1)) if cites_match else ""
        title = clean_text(title_match.group(2))
        publications.append(
            {
                "title": title,
                "normalized_title": normalize_title(title),
                "citation_count": int(cites_text) if cites_text.isdigit() else 0,
                "scholar_url": urljoin(PROFILE_URL, html.unescape(title_match.group(1))),
                "citations_url": citations_url,
            }
        )

    if not publications:
        raise ValueError("Could not parse Google Scholar publication rows")
    return publications


def match_publication_citations(local_publications: list[dict], scholar_publications: list[dict]) -> list[dict]:
    scholar_by_title = {
        item["normalized_title"]: item
        for item in scholar_publications
        if item["normalized_title"]
    }

    matched = []
    missing = []
    for publication in local_publications:
        scholar_item = scholar_by_title.get(publication["normalized_title"])
        if not scholar_item:
            missing.append(publication)
            continue

        matched.append(
            {
                "doi": publication["doi"],
                "title": publication["title"],
                "citation_count": scholar_item["citation_count"],
                "scholar_url": scholar_item["scholar_url"],
                "citations_url": scholar_item["citations_url"],
                "matched_by": "normalized_title",
                "source_title": scholar_item["title"],
            }
        )

    if missing:
        missing_titles = ", ".join(item["title"] for item in missing)
        raise ValueError(f"Missing Google Scholar citation matches for: {missing_titles}")
    return matched


def summary_title(points: list[dict]) -> str:
    return "Google Scholar citations"


def main() -> int:
    page = fetch_profile_html()
    yearly_citations = parse_yearly_citations(page)
    local_publications = load_local_publications()
    scholar_publications = parse_scholar_publications(page)
    data = {
        "profile_url": PROFILE_URL,
        "source": "Google Scholar",
        "updated": datetime.now(timezone.utc).date().isoformat(),
        "summary_title": summary_title(yearly_citations),
        "metrics": parse_metrics(page),
        "citations_by_year": yearly_citations,
        "publication_citations": match_publication_citations(
            local_publications,
            scholar_publications,
        ),
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
