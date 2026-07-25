"""Create and email scholarly sync reports for GitHub Actions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path

from scholarly_freshness import google_scholar_current_for_today, parse_iso_date


PUBLICATIONS_DIR = Path("_publications")
ABOUT_PAGE_PATH = Path("_pages/about.md")
GOOGLE_SCHOLAR_PATH = Path("_data/google_scholar.json")
EMAIL_RECIPIENT_SECRET = "SCHOLARLY_REPORT_EMAIL_TO"
DEFAULT_GOOGLE_SCHOLAR_RECENT_MAX_AGE_DAYS = 0

PUBLICATION_COMPARE_KEYS = [
    "title",
    "date",
    "venue",
    "authors",
    "first_author",
    "corresponding_author",
    "featured",
    "paperurl",
    "pdf_source",
    "originalurl",
    "link",
    "citation",
    "work_type",
    "crossref_type",
]

FIGURE_KEYS = [
    "figure_image",
    "figure_thumb",
    "figure_orientation",
    "figure_label",
    "figure_alt",
]


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repo_path_from_site_url(value: str) -> Path | None:
    value = str(value or "").strip()
    if not value or "://" in value:
        return None
    return Path(value.lstrip("/"))


def clean_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = re.match(r"---\s*\n(.*?)\n---", text, flags=re.S)
    if not match:
        return {}

    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        scalar = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if not scalar:
            continue
        key, value = scalar.groups()
        if value == "":
            continue
        fields[key] = clean_scalar(value)
    fields["front_matter_hash"] = sha256_text(match.group(1))
    return fields


def as_bool(value: str) -> bool:
    return str(value).strip().lower() == "true"


def publication_identity(fields: dict[str, str], path: Path) -> str:
    return fields.get("doi", "").lower() or path.as_posix()


def publication_snapshot(path: Path) -> dict:
    fields = parse_front_matter(path)
    figure_files = {}
    for key in FIGURE_KEYS:
        repo_path = repo_path_from_site_url(fields.get(key, ""))
        if repo_path:
            figure_files[key] = {
                "path": repo_path.as_posix(),
                "sha256": sha256_file(repo_path),
            }

    return {
        "path": path.as_posix(),
        "title": fields.get("title", ""),
        "doi": fields.get("doi", ""),
        "date": fields.get("date", ""),
        "venue": fields.get("venue", ""),
        "fields": fields,
        "figure_files": figure_files,
    }


def load_publications() -> dict[str, dict]:
    publications = {}
    if not PUBLICATIONS_DIR.exists():
        return publications
    for path in sorted(PUBLICATIONS_DIR.glob("*.md")):
        item = publication_snapshot(path)
        publications[publication_identity(item["fields"], path)] = item
    return publications


def venue_counts(items: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        venue = item["fields"].get("venue", "") or "Unknown venue"
        counts[venue] = counts.get(venue, 0) + 1
    return dict(sorted(counts.items()))


def publication_statistics(publications: dict[str, dict]) -> dict:
    items = list(publications.values())
    first_author = [item for item in items if as_bool(item["fields"].get("first_author", ""))]
    corresponding_author = [
        item for item in items if as_bool(item["fields"].get("corresponding_author", ""))
    ]
    coauthor = [
        item
        for item in items
        if not as_bool(item["fields"].get("first_author", ""))
        and not as_bool(item["fields"].get("corresponding_author", ""))
    ]
    return {
        "total": len(items),
        "first_author": len(first_author),
        "corresponding_author": len(corresponding_author),
        "coauthor": len(coauthor),
        "venues_all": venue_counts(items),
        "venues_first_author": venue_counts(first_author),
        "venues_corresponding_author": venue_counts(corresponding_author),
        "venues_coauthor": venue_counts(coauthor),
    }


def extract_news() -> dict:
    if not ABOUT_PAGE_PATH.exists():
        return {"path": ABOUT_PAGE_PATH.as_posix(), "exists": False, "hash": "", "items": []}
    text = ABOUT_PAGE_PATH.read_text(encoding="utf-8")
    match = re.search(r"## News\s*\n\s*<ul class=\"site-news\">\s*\n(.*?)\s*</ul>", text, flags=re.S)
    if not match:
        return {"path": ABOUT_PAGE_PATH.as_posix(), "exists": True, "hash": "", "items": []}
    body = match.group(1).strip()
    items = [re.sub(r"\s+", " ", item.strip()) for item in re.findall(r"<li\b.*?</li>", body, flags=re.S)]
    return {
        "path": ABOUT_PAGE_PATH.as_posix(),
        "exists": True,
        "hash": sha256_text(body),
        "items": items,
    }


def load_google_scholar() -> dict:
    if not GOOGLE_SCHOLAR_PATH.exists():
        return {"exists": False}
    data = json.loads(GOOGLE_SCHOLAR_PATH.read_text(encoding="utf-8"))
    publication_citations = {}
    for item in data.get("publication_citations", []):
        key = str(item.get("doi", "")).lower()
        if key:
            publication_citations[key] = {
                "title": item.get("title", ""),
                "citation_count": item.get("citation_count", 0),
                "scholar_url": item.get("scholar_url", ""),
            }
    return {
        "exists": True,
        "updated": data.get("updated", ""),
        "last_attempted": data.get("last_attempted", ""),
        "sync_status": data.get("sync_status", ""),
        "last_error": data.get("last_error", ""),
        "sync_provider": data.get("sync_provider", ""),
        "metrics": data.get("metrics", {}),
        "citations_by_year": data.get("citations_by_year", []),
        "publication_citations": publication_citations,
        "sha256": sha256_text(json.dumps(data, sort_keys=True, ensure_ascii=False)),
    }


def google_scholar_recent_enough(data: dict) -> bool:
    if data.get("exists") is not True or data.get("sync_status") != "ok":
        return False
    updated = parse_iso_date(data.get("updated", ""))
    if not updated:
        return False
    age_days = (datetime.now(timezone.utc).date() - updated).days
    return 0 <= age_days <= google_scholar_recent_max_age_days()


def google_scholar_recent_max_age_days() -> int:
    value = os.environ.get("GOOGLE_SCHOLAR_RECENT_MAX_AGE_DAYS", "").strip()
    if not value:
        return DEFAULT_GOOGLE_SCHOLAR_RECENT_MAX_AGE_DAYS
    return max(0, int(value))


def snapshot() -> dict:
    publications = load_publications()
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "publications": publications,
        "statistics": publication_statistics(publications),
        "news": extract_news(),
        "google_scholar": load_google_scholar(),
    }


def describe_publication(item: dict) -> str:
    parts = [item.get("title", "Untitled")]
    detail = ", ".join(
        value
        for value in [item.get("venue", ""), item.get("date", ""), item.get("doi", "")]
        if value
    )
    if detail:
        parts.append(f"({detail})")
    return " ".join(parts)


def changed_fields(before_fields: dict, after_fields: dict, keys: list[str]) -> list[str]:
    changes = []
    for key in keys:
        old = before_fields.get(key, "")
        new = after_fields.get(key, "")
        if old != new:
            changes.append(f"{key}: {old or '[empty]'} -> {new or '[empty]'}")
    return changes


def statistics_lines(before: dict, after: dict) -> list[str]:
    lines = []
    for key in ["total", "first_author", "corresponding_author", "coauthor"]:
        if before.get(key) != after.get(key):
            lines.append(f"- {key}: {before.get(key, 0)} -> {after.get(key, 0)}")
    for key in ["venues_all", "venues_first_author", "venues_corresponding_author", "venues_coauthor"]:
        if before.get(key) != after.get(key):
            old = json.dumps(before.get(key, {}), ensure_ascii=False, sort_keys=True)
            new = json.dumps(after.get(key, {}), ensure_ascii=False, sort_keys=True)
            lines.append(f"- {key}: {old} -> {new}")
    return lines


def scholar_metric_lines(before: dict, after: dict) -> list[str]:
    lines = []
    for metric_name in ["citations", "h_index", "i10_index"]:
        before_metric = before.get("metrics", {}).get(metric_name, {})
        after_metric = after.get("metrics", {}).get(metric_name, {})
        for scope in ["all", "recent"]:
            if before_metric.get(scope) != after_metric.get(scope):
                lines.append(
                    f"- {metric_name}.{scope}: {before_metric.get(scope, 0)} -> {after_metric.get(scope, 0)}"
                )

    before_years = {item.get("year"): item.get("citations") for item in before.get("citations_by_year", [])}
    after_years = {item.get("year"): item.get("citations") for item in after.get("citations_by_year", [])}
    for year in sorted(set(before_years) | set(after_years)):
        if before_years.get(year) != after_years.get(year):
            lines.append(f"- citations_by_year.{year}: {before_years.get(year, 0)} -> {after_years.get(year, 0)}")

    before_papers = before.get("publication_citations", {})
    after_papers = after.get("publication_citations", {})
    for key in sorted(set(before_papers) | set(after_papers)):
        old = before_papers.get(key, {}).get("citation_count")
        new = after_papers.get(key, {}).get("citation_count")
        if old != new:
            title = after_papers.get(key, {}).get("title") or before_papers.get(key, {}).get("title") or key
            lines.append(f"- {title}: {old if old is not None else 0} -> {new if new is not None else 0}")
    return lines


def figure_lines(before_pubs: dict, after_pubs: dict) -> list[str]:
    lines = []
    for key in sorted(set(after_pubs) - set(before_pubs)):
        item = after_pubs[key]
        figure_fields = [
            f"{field}: {item['fields'].get(field, '')}"
            for field in FIGURE_KEYS
            if item["fields"].get(field, "")
        ]
        if figure_fields or item.get("figure_files"):
            lines.append(f"- New figure data for {describe_publication(item)}")
            lines.extend(f"  - {field}" for field in figure_fields)
    for key in sorted(set(before_pubs) - set(after_pubs)):
        item = before_pubs[key]
        figure_fields = [
            f"{field}: {item['fields'].get(field, '')}"
            for field in FIGURE_KEYS
            if item["fields"].get(field, "")
        ]
        if figure_fields or item.get("figure_files"):
            lines.append(f"- Removed figure data for {describe_publication(item)}")
            lines.extend(f"  - {field}" for field in figure_fields)
    for key in sorted(set(before_pubs) & set(after_pubs)):
        before_item = before_pubs[key]
        after_item = after_pubs[key]
        field_changes = changed_fields(before_item["fields"], after_item["fields"], FIGURE_KEYS)
        file_changes = []
        before_files = before_item.get("figure_files", {})
        after_files = after_item.get("figure_files", {})
        for figure_key in sorted(set(before_files) | set(after_files)):
            old = before_files.get(figure_key, {})
            new = after_files.get(figure_key, {})
            if old.get("sha256") != new.get("sha256"):
                file_changes.append(f"{figure_key} file hash changed ({old.get('path', '') or new.get('path', '')})")
        if field_changes or file_changes:
            lines.append(f"- {describe_publication(after_item)}")
            lines.extend(f"  - {change}" for change in field_changes + file_changes)
    return lines


def build_report(before: dict, after: dict, scholar_status: dict | None = None) -> tuple[str, dict]:
    before_pubs = before.get("publications", {})
    after_pubs = after.get("publications", {})
    before_keys = set(before_pubs)
    after_keys = set(after_pubs)

    new_publications = [after_pubs[key] for key in sorted(after_keys - before_keys)]
    removed_publications = [before_pubs[key] for key in sorted(before_keys - after_keys)]
    updated_publications = []
    for key in sorted(before_keys & after_keys):
        changes = changed_fields(before_pubs[key]["fields"], after_pubs[key]["fields"], PUBLICATION_COMPARE_KEYS)
        if changes:
            updated_publications.append((after_pubs[key], changes))

    stats = statistics_lines(before.get("statistics", {}), after.get("statistics", {}))
    news_changed = before.get("news", {}).get("hash") != after.get("news", {}).get("hash")
    figures = figure_lines(before_pubs, after_pubs)
    scholar = scholar_metric_lines(before.get("google_scholar", {}), after.get("google_scholar", {}))
    scholar_attempt_alert = bool(
        scholar_status
        and (
            scholar_status.get("used_cache")
            or scholar_status.get("status") == "failed"
        )
    )
    after_scholar = after.get("google_scholar", {})
    scholar_already_current = google_scholar_current_for_today(after_scholar)
    scholar_recent_enough = google_scholar_recent_enough(after_scholar)
    scholar_sync_alert = scholar_attempt_alert and not scholar_recent_enough

    has_changes = any(
        [
            new_publications,
            removed_publications,
            updated_publications,
            stats,
            news_changed,
            figures,
            scholar,
            scholar_sync_alert,
        ]
    )

    lines = [
        "# Scholarly data update report",
        "",
        f"- Captured before: {before.get('captured_at', '')}",
        f"- Captured after: {after.get('captured_at', '')}",
        f"- Changes or alerts detected: {'yes' if has_changes else 'no'}",
        "",
        "## Publications",
    ]

    if new_publications:
        lines.append("New publications:")
        lines.extend(f"- {describe_publication(item)}" for item in new_publications)
    else:
        lines.append("New publications: none")

    if removed_publications:
        lines.append("Removed publications:")
        lines.extend(f"- {describe_publication(item)}" for item in removed_publications)
    else:
        lines.append("Removed publications: none")

    if updated_publications:
        lines.append("Updated publications:")
        for item, changes in updated_publications:
            lines.append(f"- {describe_publication(item)}")
            lines.extend(f"  - {change}" for change in changes)
    else:
        lines.append("Updated publications: none")

    lines.extend(["", "## News"])
    if news_changed:
        old_count = len(before.get("news", {}).get("items", []))
        new_count = len(after.get("news", {}).get("items", []))
        lines.append(f"- News changed: yes ({old_count} items -> {new_count} items)")
    else:
        lines.append("- News changed: no")

    lines.extend(["", "## Publication Count And Statistics"])
    lines.extend(stats or ["- Statistics changed: no"])

    lines.extend(["", "## Thumbnails And Figures"])
    lines.extend(figures or ["- Thumbnail/figure fields or files changed: no"])

    lines.extend(["", "## Google Scholar Metrics"])
    if scholar_status:
        status = scholar_status.get("status", "")
        provider = scholar_status.get("provider", "")
        provider_label = f" ({provider})" if provider else ""
        used_cache = scholar_status.get("used_cache", False)
        if used_cache:
            if scholar_recent_enough:
                lines.append(
                    "- Latest Google Scholar attempt used cached data"
                    f"{provider_label}, but the public data is recent enough "
                    f"(updated {after_scholar.get('updated', 'unknown')}; "
                    f"alert threshold: {google_scholar_recent_max_age_days()} days)."
                )
            else:
                lines.append(
                    f"- Latest Google Scholar attempt used cached data{provider_label}: "
                    f"{scholar_status.get('error', '')}"
                )
            if scholar_status.get("committed_stale_status") is False:
                lines.append(
                    "- Cached data file was left unchanged to avoid publishing a stale-status-only website update."
                )
        else:
            lines.append(f"- Latest Google Scholar attempt status: {status or 'unknown'}{provider_label}")
    lines.extend(scholar or ["- Google Scholar metrics changed: no"])

    report = "\n".join(lines).rstrip() + "\n"
    metadata = {
        "has_changes": has_changes,
        "new_publications": len(new_publications),
        "removed_publications": len(removed_publications),
        "updated_publications": len(updated_publications),
        "news_changed": news_changed,
        "statistics_changed": bool(stats),
        "figures_changed": bool(figures),
        "google_scholar_changed": bool(scholar),
        "google_scholar_sync_alert": scholar_sync_alert,
        "google_scholar_already_current": scholar_already_current,
        "google_scholar_recent_enough": scholar_recent_enough,
        "google_scholar_recent_max_age_days": google_scholar_recent_max_age_days(),
        "scholar_status": scholar_status or {},
    }
    return report, metadata


def write_github_output(metadata: dict) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as handle:
        handle.write(f"has_changes={'true' if metadata.get('has_changes') else 'false'}\n")
        handle.write(
            "google_scholar_sync_alert="
            f"{'true' if metadata.get('google_scholar_sync_alert') else 'false'}\n"
        )


def append_summary(text: str) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write(text.rstrip() + "\n")


def read_json_if_exists(path: str | None) -> dict | None:
    if not path:
        return None
    candidate = Path(path)
    if not candidate.exists():
        return None
    return json.loads(candidate.read_text(encoding="utf-8-sig"))


def command_snapshot(args: argparse.Namespace) -> int:
    data = snapshot()
    Path(args.output).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote scholarly snapshot to {args.output}")
    return 0


def command_report(args: argparse.Namespace) -> int:
    before = json.loads(Path(args.before).read_text(encoding="utf-8"))
    after = snapshot()
    scholar_status = read_json_if_exists(args.scholar_status)
    report, metadata = build_report(before, after, scholar_status)
    Path(args.output).write_text(report, encoding="utf-8")
    if args.json_output:
        Path(args.json_output).write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if args.append_summary:
        append_summary(report)
    write_github_output(metadata)
    print(f"Wrote scholarly report to {args.output}")
    return 0


def email_settings(recipient_override: str = "") -> tuple[dict[str, str], list[str], str]:
    values = {
        "SMTP_HOST": os.environ.get("SMTP_HOST", "").strip(),
        "SMTP_PORT": os.environ.get("SMTP_PORT", "").strip(),
        "SMTP_USERNAME": os.environ.get("SMTP_USERNAME", "").strip(),
        "SMTP_PASSWORD": os.environ.get("SMTP_PASSWORD", "").strip(),
        "SMTP_FROM": os.environ.get("SMTP_FROM", "").strip(),
        "SMTP_SECURITY": os.environ.get("SMTP_SECURITY", "starttls").strip().lower(),
    }
    recipient = (recipient_override or os.environ.get("REPORT_EMAIL_TO", "")).strip()
    missing = []
    if not recipient:
        missing.append(EMAIL_RECIPIENT_SECRET)
    missing.extend(key for key in ["SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD"] if not values[key])
    if not values["SMTP_FROM"]:
        values["SMTP_FROM"] = values["SMTP_USERNAME"]
    return values, missing, recipient


def command_email(args: argparse.Namespace) -> int:
    report_text = Path(args.report).read_text(encoding="utf-8")
    report_metadata = read_json_if_exists(args.report_json) or {}
    if args.only_if_changed and not report_metadata.get("has_changes", True):
        message = "## Email notification\nEmail not sent because scholarly data did not change."
        append_summary(message)
        print("Email not sent because scholarly data did not change.")
        return 0

    values, missing, recipient = email_settings(args.to)
    if missing:
        message = (
            "## Email notification\n"
            "Email was not sent because these GitHub Actions secrets are missing: "
            + ", ".join(missing)
            + ".\n"
            "The scholarly update report is still included above in the Actions summary."
        )
        append_summary(message)
        print(message, file=sys.stderr)
        return 0

    if args.dry_run:
        message = "## Email notification\nDry run: email would be sent to the configured recipient."
        append_summary(message)
        print("Dry run: email would be sent to the configured recipient.")
        return 0

    smtp_port = int(values["SMTP_PORT"])
    email_message = EmailMessage()
    email_message["Subject"] = args.subject
    email_message["From"] = values["SMTP_FROM"]
    email_message["To"] = recipient
    email_message.set_content(report_text)

    if values["SMTP_SECURITY"] == "ssl":
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(values["SMTP_HOST"], smtp_port, context=context, timeout=30) as smtp:
            smtp.login(values["SMTP_USERNAME"], values["SMTP_PASSWORD"])
            smtp.send_message(email_message)
    else:
        with smtplib.SMTP(values["SMTP_HOST"], smtp_port, timeout=30) as smtp:
            if values["SMTP_SECURITY"] != "none":
                smtp.starttls(context=ssl.create_default_context())
            smtp.login(values["SMTP_USERNAME"], values["SMTP_PASSWORD"])
            smtp.send_message(email_message)

    message = "## Email notification\nEmail sent to the configured recipient."
    append_summary(message)
    print("Email sent to the configured recipient.")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--output", required=True)
    snapshot_parser.set_defaults(func=command_snapshot)

    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--before", required=True)
    report_parser.add_argument("--output", required=True)
    report_parser.add_argument("--json-output", default="")
    report_parser.add_argument("--scholar-status", default="")
    report_parser.add_argument("--append-summary", action="store_true")
    report_parser.set_defaults(func=command_report)

    email_parser = subparsers.add_parser("email")
    email_parser.add_argument("--report", required=True)
    email_parser.add_argument("--report-json", default="")
    email_parser.add_argument("--to", default="")
    email_parser.add_argument("--subject", default="Scholarly data update report")
    email_parser.add_argument("--only-if-changed", action="store_true")
    email_parser.add_argument("--dry-run", action="store_true")
    email_parser.set_defaults(func=command_email)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
