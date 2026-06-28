"""Generate manual-review reminders for publication media coverage."""

from __future__ import annotations

import argparse
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import quote_plus


PUBLICATIONS_DIR = Path("_publications")
AUTHOR_QUERY = '"Fan Cheng"'


@dataclass(frozen=True)
class Publication:
    path: Path
    title: str
    publication_date: date | None
    venue: str
    doi: str
    first_author: bool
    featured: bool
    media_coverage_count: int
    video_interview_count: int
    has_opn: bool


def clean_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def front_matter_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\s*\n(.*?)\n---", text, flags=re.S)
    return match.group(1) if match else ""


def parse_scalar_fields(front_matter: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in front_matter.splitlines():
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if not match:
            continue
        key, value = match.groups()
        if value:
            fields[key] = clean_scalar(value)
    return fields


def count_list_items(front_matter: str, key: str) -> int:
    key_pattern = re.compile(rf"^{re.escape(key)}:\s*$")
    next_key_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*:\s*")
    in_block = False
    count = 0
    for line in front_matter.splitlines():
        if not in_block:
            in_block = bool(key_pattern.match(line))
            continue
        if next_key_pattern.match(line):
            break
        if re.match(r"^\s*-\s+", line):
            count += 1
    return count


def as_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def parse_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def load_publication(path: Path) -> Publication:
    front_matter = front_matter_text(path)
    fields = parse_scalar_fields(front_matter)
    return Publication(
        path=path,
        title=fields.get("title", path.stem),
        publication_date=parse_date(fields.get("date", "")),
        venue=fields.get("venue", ""),
        doi=fields.get("doi", ""),
        first_author=as_bool(fields.get("first_author", "")),
        featured=as_bool(fields.get("featured", "")),
        media_coverage_count=count_list_items(front_matter, "media_coverage"),
        video_interview_count=count_list_items(front_matter, "video_interviews"),
        has_opn=bool(fields.get("opn_url", "")),
    )


def load_publications() -> list[Publication]:
    if not PUBLICATIONS_DIR.exists():
        return []
    return [load_publication(path) for path in sorted(PUBLICATIONS_DIR.glob("*.md"))]


def selected_publications(
    publications: list[Publication],
    today: date,
    lookback_days: int,
) -> list[Publication]:
    selected = []
    for publication in publications:
        if not publication.publication_date:
            continue
        age_days = (today - publication.publication_date).days
        if 0 <= age_days <= lookback_days:
            selected.append(publication)
    return sorted(
        selected,
        key=lambda item: (
            item.publication_date or date.min,
            item.featured,
            item.first_author,
            item.title.lower(),
        ),
        reverse=True,
    )


def search_url(engine: str, query: str) -> str:
    encoded = quote_plus(query)
    if engine == "google_news":
        return (
            "https://news.google.com/search?q="
            f"{encoded}&hl=en-US&gl=US&ceid=US:en"
        )
    if engine == "google_web":
        return f"https://www.google.com/search?q={encoded}"
    if engine == "bing_news":
        return f"https://www.bing.com/news/search?q={encoded}"
    if engine == "bing_web":
        return f"https://www.bing.com/search?q={encoded}"
    raise ValueError(f"Unsupported search engine: {engine}")


def publication_queries(publication: Publication) -> list[tuple[str, str]]:
    exact_title = f'"{publication.title}"'
    title_author = f"{exact_title} {AUTHOR_QUERY}"
    title_doi = f'{exact_title} "{publication.doi}"' if publication.doi else exact_title
    return [
        ("Google News: exact title + author", search_url("google_news", title_author)),
        ("Google Web: exact title + author", search_url("google_web", title_author)),
        ("Bing News: exact title + author", search_url("bing_news", title_author)),
        ("Google Web: exact title + DOI", search_url("google_web", title_doi)),
        ("Bing Web: exact title only", search_url("bing_web", exact_title)),
    ]


def status_text(publication: Publication) -> str:
    parts = [f"{publication.media_coverage_count} media links on site"]
    parts.append("OPN listed" if publication.has_opn else "OPN not listed")
    parts.append(f"{publication.video_interview_count} video interviews")
    return "; ".join(parts)


def build_report(
    publications: list[Publication],
    today: date,
    lookback_days: int,
) -> tuple[str, dict[str, object]]:
    candidates = selected_publications(publications, today, lookback_days)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# Media coverage candidate reminder",
        "",
        f"- Generated: {generated_at}",
        f"- Review window: publications from the last {lookback_days} days",
        f"- Candidate publications: {len(candidates)}",
        "- Email recipient: GitHub Actions secret SCHOLARLY_REPORT_EMAIL_TO. "
        "GitHub hides the real address, so it is not stored in this repository.",
        "- Policy: this report only creates manual-review search links; it does "
        "not edit the website or add media coverage automatically.",
        "",
        "## When To Check",
        "",
        "- Normal cadence: once per week during the first 90 days after publication.",
        "- After 90 days: do not keep weekly checks by default; run the workflow "
        "manually after a press release, conference talk, institution news post, "
        "award, or known article pickup.",
        "- Website rule: add an item only after checking that the source is real, "
        "substantive, directly about the paper, and not just a duplicated low-value "
        "aggregation page.",
        "",
        "## Candidates",
        "",
    ]
    if not candidates:
        lines.append("- No publications are inside the current review window.")
    for index, publication in enumerate(candidates, start=1):
        date_text = publication.publication_date.isoformat()
        detail = ", ".join(
            value
            for value in [publication.venue, date_text, publication.doi]
            if value
        )
        lines.extend(
            [
                f"### {index}. {publication.title}",
                "",
                f"- Details: {detail}",
                f"- Current site state: {status_text(publication)}",
                f"- Source file: `{publication.path.as_posix()}`",
                "- Search links:",
            ]
        )
        lines.extend(f"  - [{label}]({url})" for label, url in publication_queries(publication))
        lines.append("")

    report = "\n".join(lines).rstrip() + "\n"
    metadata = {
        "generated_at": generated_at,
        "review_window_days": lookback_days,
        "candidate_count": len(candidates),
        "candidate_titles": [publication.title for publication in candidates],
    }
    return report, metadata


def append_summary(text: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def write_github_output(metadata: dict[str, object]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    has_candidates = bool(metadata.get("candidate_count", 0))
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"has_candidates={'true' if has_candidates else 'false'}\n")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--json-output", default="")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--today", default="")
    parser.add_argument("--append-summary", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    today = date.fromisoformat(args.today) if args.today else date.today()
    report, metadata = build_report(load_publications(), today, args.days)
    Path(args.output).write_text(report, encoding="utf-8")
    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if args.append_summary:
        append_summary(report)
    write_github_output(metadata)
    print(f"Wrote media coverage reminder to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
