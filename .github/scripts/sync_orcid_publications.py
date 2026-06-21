"""Sync ORCID works into Academic Pages publication markdown files."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


ORCID_ID = "0000-0003-3088-2983"
AUTHOR_NAME = "Fan Cheng"
OUTPUT_DIR = Path("_publications")
PDF_DIR = Path("files/papers")
JOURNAL_METRICS_PATH = Path("_data/journal_metrics.json")
ABOUT_PAGE_PATH = Path("_pages/about.md")
USER_AGENT = "fancheng5640.github.io ORCID sync (mailto:fancheng@mail.tau.ac.il)"
RECENT_NEWS_YEAR_WINDOW = 5

ALLOWED_ORCID_WORK_TYPES = {"journal-article"}
ALLOWED_CROSSREF_TYPES = {"journal-article"}


JOURNAL_METRICS = {
    "Nature Communications": {
        "impact_factor": 18.1,
        "impact_factor_year": 2025,
        "impact_factor_source": "https://wos-journal.info/journalid/11621",
    },
    "Optica": {
        "impact_factor": 8.8,
        "impact_factor_year": 2025,
        "impact_factor_source": "https://wos-journal.info/journalid/15214",
    },
    "Photonics Research": {
        "impact_factor": 7.1,
        "impact_factor_year": 2025,
        "impact_factor_source": "https://wos-journal.info/journalid/2608",
    },
    "Applied Physics Letters": {
        "impact_factor": 3.8,
        "impact_factor_year": 2025,
        "impact_factor_source": "https://wos-journal.info/journalid/14441",
    },
    "Optics Express": {
        "impact_factor": 3.4,
        "impact_factor_year": 2025,
        "impact_factor_source": "https://wos-journal.info/journalid/14662",
    },
    "AIP Advances": {
        "impact_factor": 1.7,
        "impact_factor_year": 2025,
        "impact_factor_source": "https://wos-journal.info/journalid/20191",
    },
}


# ORCID and Crossref do not reliably expose corresponding-author status.
# Add DOI keys here when a paper should be shown in the corresponding-author
# summary section.
ROLE_OVERRIDES = {
    # "10.0000/example": {"corresponding_author": True},
}

CORRESPONDING_AUTHOR_NAMES = {
    "10.1364/oe.26.031500": {"Pengfei Zhang"},
    "10.1038/s41467-023-40205-0": {"Tal Carmon"},
    "10.1364/prj.505164": {"Tal Carmon"},
    "10.1063/5.0197109": {"Lev Deych"},
    "10.1364/oe.561188": {"Tal Carmon"},
    "10.1364/optica.560597": {"Tal Carmon"},
    "10.1063/5.0279509": {"Tal Carmon"},
}

PDF_OVERRIDES = {
    "10.1063/5.0279509": [
        "https://einstein.nju.edu.cn/upload/uploadify/20250925/20250922-AppliedPhysicsLetters_202509251317130813.pdf",
    ],
    "10.1364/optica.560597": [
        "https://einstein.nju.edu.cn/upload/uploadify/20250925/20250920-Optica_202509251317069839.pdf",
        "https://arxiv.org/pdf/2507.04484",
    ],
    "10.1364/prj.505164": [
        "https://arxiv.org/pdf/2312.12632",
    ],
    "10.1063/5.0197109": [
        "https://arxiv.org/pdf/2401.00954",
    ],
    "10.1364/oe.26.031500": [
        "https://ioe.sxu.edu.cn/docs//2022-09/6e9509a2918c44f69c8f0de112e1bcc7.pdf",
    ],
}

PDF_FILENAMES = {
    "10.1364/oe.26.031500": "2018-opt-express-nanofiber-diameter.pdf",
    "10.1038/s41467-023-40205-0": "2023-nat-commun-plasma-microphotonics.pdf",
    "10.1364/prj.505164": "2024-photonics-research-cavity-continuum.pdf",
    "10.1063/5.0197109": "2024-aip-adv-levitating-mirror.pdf",
    "10.1364/oe.561188": "2025-opt-express-mode-coalescence.pdf",
    "10.1364/optica.560597": "2025-optica-photonic-origami.pdf",
    "10.1063/5.0279509": "2025-apl-droplet-evaporation.pdf",
}

NEWS_PUBLICATION_VARIABLES = {
    "10.1063/5.0279509": "pub_apl_2025",
    "10.1364/optica.560597": "pub_optica_2025",
    "10.1364/oe.561188": "pub_oe_2025",
    "10.1364/prj.505164": "pub_pr_2024",
    "10.1063/5.0197109": "pub_aip_2024",
    "10.1038/s41467-023-40205-0": "pub_nc_2023",
    "10.1364/oe.26.031500": "pub_oe_2018",
}

NEWS_FEATURED_MEDIA = {
    "10.1364/optica.560597": {
        "name": "Optics & Photonics News",
        "logo": "/files/papers/figures/logos/optics-photonics-news-logo.svg",
    },
    "10.1038/s41467-023-40205-0": {
        "name": "Optics & Photonics News",
        "logo": "/files/papers/figures/logos/optics-photonics-news-logo.svg",
    },
}

AUTO_METADATA_KEYS = {
    "title",
    "collection",
    "category",
    "orcid_sync",
    "source_orcid",
    "doi",
    "work_type",
    "crossref_type",
    "first_author",
    "corresponding_author",
    "featured",
    "journal_impact_factor",
    "impact_factor_year",
    "impact_factor_source",
    "permalink",
    "excerpt",
    "date",
    "venue",
    "authors",
    "author_entries",
    "originalurl",
    "link",
    "paperurl",
    "pdf_source",
    "citation",
}


def load_journal_metrics() -> dict:
    if not JOURNAL_METRICS_PATH.exists():
        return JOURNAL_METRICS
    data = json.loads(JOURNAL_METRICS_PATH.read_text(encoding="utf-8"))
    metric_year = data.get("metadata", {}).get("metric_year", "")
    metrics = {}
    for journal in data.get("journals", []):
        name = journal.get("name", "")
        if not name:
            continue
        metrics[name] = {
            "impact_factor": journal.get("impact_factor", 0),
            "impact_factor_year": metric_year,
            "impact_factor_source": journal.get("source", ""),
        }
    return metrics


def normalized_work_type(value: object) -> str:
    return str(value or "").strip().lower()


def is_journal_article_type(value: object, allowed_types: set[str]) -> bool:
    return normalized_work_type(value) in allowed_types


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def fetch_bytes(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/pdf,*/*;q=0.8",
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return response.read()


def text_value(value: dict | None, default: str = "") -> str:
    if not value:
        return default
    return value.get("value") or default


def date_from_orcid(publication_date: dict | None) -> str:
    if not publication_date:
        return "1900-01-01"
    year = text_value(publication_date.get("year"), "1900")
    month = text_value(publication_date.get("month"), "01").zfill(2)
    day = text_value(publication_date.get("day"), "01").zfill(2)
    return f"{year}-{month}-{day}"


def doi_from_summary(summary: dict) -> str:
    for external_id in summary.get("external-ids", {}).get("external-id", []):
        if external_id.get("external-id-type") == "doi":
            return external_id.get("external-id-value", "").strip()
    return ""


def fetch_crossref(doi: str) -> dict:
    encoded = urllib.parse.quote(doi, safe="")
    data = fetch_json(f"https://api.crossref.org/works/{encoded}")
    return data["message"]


def author_name(author: dict) -> str:
    given = author.get("given", "").strip()
    family = author.get("family", "").strip()
    return " ".join(part for part in [given, family] if part).strip()


def author_list(crossref_message: dict) -> list[str]:
    names = [author_name(author) for author in crossref_message.get("author", [])]
    return [name for name in names if name]


def english_author_join(authors: list[str]) -> str:
    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return ", ".join(authors[:-1]) + f", and {authors[-1]}"


def html_author_join(authors: list[str]) -> str:
    highlighted = []
    for author in authors:
        escaped = html.escape(author)
        if author.lower() == AUTHOR_NAME.lower():
            highlighted.append(f"<strong><u>{escaped}</u></strong>")
        else:
            highlighted.append(escaped)
    return english_author_join(highlighted)


def author_entries(authors: list[str], doi: str) -> list[dict[str, object]]:
    corresponding_names = {
        name.lower() for name in CORRESPONDING_AUTHOR_NAMES.get(doi.lower(), set())
    }
    entries = []
    for author in authors:
        entry: dict[str, object] = {"name": author}
        if author.lower() in corresponding_names:
            entry["corresponding"] = True
        entries.append(entry)
    return entries


def pdf_urls_from_crossref(crossref_message: dict) -> list[str]:
    urls = []
    for link in crossref_message.get("link", []):
        url = link.get("URL", "")
        content_type = link.get("content-type", "")
        if content_type == "application/pdf" or "viewmedia.cfm" in url:
            urls.append(url)
    return urls


def write_if_changed(path: Path, content: bytes) -> None:
    if path.exists() and path.read_bytes() == content:
        return
    path.write_bytes(content)


def download_pdf(pdf_url: str, path: Path) -> bool:
    if not pdf_url:
        return False
    try:
        content = fetch_bytes(pdf_url)
    except (urllib.error.URLError, TimeoutError) as exc:
        print(f"WARNING: PDF download failed for {pdf_url}: {exc}", file=sys.stderr)
        return False
    if b"%PDF" not in content[:1024]:
        print(f"WARNING: PDF download did not return a PDF: {pdf_url}", file=sys.stderr)
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    write_if_changed(path, content)
    return True


def download_first_pdf(candidates: list[str], path: Path) -> str:
    if path.exists():
        return ""
    for pdf_url in candidates:
        if download_pdf(pdf_url, path):
            return pdf_url
    return ""


def crossref_date(crossref_message: dict, fallback: str) -> str:
    for key in ["published-print", "published-online", "published"]:
        parts = crossref_message.get(key, {}).get("date-parts", [[]])[0]
        if parts:
            year = str(parts[0])
            month = str(parts[1]).zfill(2) if len(parts) > 1 else "01"
            day = str(parts[2]).zfill(2) if len(parts) > 2 else "01"
            return f"{year}-{month}-{day}"
    return fallback


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    return slug.strip("-")


def yaml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return json.dumps(str(value), ensure_ascii=False)


def front_matter(metadata: dict) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def split_front_matter(text: str) -> tuple[list[str], str]:
    match = re.match(r"---\s*\n(.*?)\n---\s*(.*)$", text, flags=re.S)
    if not match:
        return [], text
    return match.group(1).splitlines(), match.group(2)


def scalar_front_matter_values(lines: list[str]) -> dict:
    values = {}
    for line in lines:
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*?)\s*$", line)
        if not match:
            continue
        key, value = match.groups()
        values[key] = value.strip().strip('"').strip("'")
    return values


def load_existing_publications() -> dict:
    existing = {}
    if not OUTPUT_DIR.exists():
        return existing

    for path in OUTPUT_DIR.glob("*.md"):
        if not is_generated_publication(path):
            continue
        text = path.read_text(encoding="utf-8")
        front_lines, body = split_front_matter(text)
        metadata = scalar_front_matter_values(front_lines)
        doi = metadata.get("doi", "").lower()
        if doi:
            existing[doi] = {
                "path": path,
                "front_lines": front_lines,
                "body": body,
                "metadata": metadata,
            }
    return existing


def merge_existing_publication(existing: dict | None, metadata: dict, fallback_body: str) -> str:
    if not existing:
        return front_matter(metadata) + fallback_body

    seen = set()
    merged_lines = ["---"]
    skip_replaced_block = False
    for line in existing["front_lines"]:
        if skip_replaced_block:
            if re.match(r"^\s+", line) or not line.strip():
                continue
            skip_replaced_block = False
        match = re.match(r"^([A-Za-z_][A-Za-z0-9_-]*):", line)
        if match and match.group(1) in AUTO_METADATA_KEYS:
            key = match.group(1)
            merged_lines.append(f"{key}: {yaml_value(metadata[key])}")
            seen.add(key)
            skip_replaced_block = isinstance(metadata[key], (dict, list))
        else:
            merged_lines.append(line)

    for key, value in metadata.items():
        if key not in seen and key in AUTO_METADATA_KEYS:
            merged_lines.append(f"{key}: {yaml_value(value)}")

    merged_lines.append("---")
    body = existing.get("body") or fallback_body
    if not body.startswith("\n"):
        body = "\n\n" + body
    return "\n".join(merged_lines) + body


def publication_record(
    summary: dict,
    existing_publications: dict,
    *,
    download_pdfs: bool = True,
) -> dict | None:
    doi = doi_from_summary(summary)
    if not doi:
        return None
    work_type = normalized_work_type(summary.get("type"))
    if not is_journal_article_type(work_type, ALLOWED_ORCID_WORK_TYPES):
        print(
            f"Skipping non-journal ORCID work type {work_type or 'unknown'} for {doi}",
            file=sys.stderr,
        )
        return None
    existing_publication = existing_publications.get(doi.lower())
    existing_metadata = existing_publication.get("metadata", {}) if existing_publication else {}
    title = summary["title"]["title"]["value"].strip()
    date = date_from_orcid(summary.get("publication-date"))
    journal = text_value(summary.get("journal-title"), "")

    try:
        crossref = fetch_crossref(doi)
        time.sleep(0.1)
    except (urllib.error.URLError, KeyError, TimeoutError) as exc:
        print(f"WARNING: Crossref lookup failed for {doi}: {exc}", file=sys.stderr)
        crossref = {}

    crossref_type = normalized_work_type(crossref.get("type")) if crossref else ""
    if crossref_type and not is_journal_article_type(crossref_type, ALLOWED_CROSSREF_TYPES):
        print(
            f"Skipping non-journal Crossref work type {crossref_type} for {doi}",
            file=sys.stderr,
        )
        return None

    authors = author_list(crossref)
    if crossref:
        title = (crossref.get("title") or [title])[0].strip()
        journal = (crossref.get("container-title") or [journal])[0].strip()
        date = crossref_date(crossref, date)

    volume = str(crossref.get("volume", "")).strip()
    issue = str(crossref.get("issue", "")).strip()
    page = str(crossref.get("page") or crossref.get("article-number") or "").strip()

    metrics = JOURNAL_METRICS.get(journal, {})
    first_author = bool(authors and authors[0].lower() == AUTHOR_NAME.lower())
    overrides = ROLE_OVERRIDES.get(doi.lower(), {})
    corresponding_author = bool(overrides.get("corresponding_author", False))
    featured = bool(overrides.get("featured", first_author))

    citation_bits = [english_author_join(authors), f"({date[:4]})."]
    citation = " ".join(bit for bit in citation_bits if bit).strip()
    citation += f" &quot;{html.escape(title)}.&quot;"
    if journal:
        citation += f" <i>{html.escape(journal)}</i>"
    details = []
    if volume:
        details.append(volume)
    if issue:
        details[-1] = f"{details[-1]}({issue})" if details else f"({issue})"
    if page:
        details.append(page)
    if details:
        citation += ", " + ", ".join(details)
    citation += f". https://doi.org/{doi}"
    citation = citation.replace(
        AUTHOR_NAME, f"<strong><u>{html.escape(AUTHOR_NAME)}</u></strong>"
    )

    date_slug = date
    slug = f"{date_slug}-{slugify(title)}"
    filename = f"{slug}.md"
    pdf_filename = PDF_FILENAMES.get(doi.lower(), f"{slug}.pdf")
    pdf_path = PDF_DIR / pdf_filename
    pdf_candidates = PDF_OVERRIDES.get(doi.lower(), []) + pdf_urls_from_crossref(crossref)
    pdf_source = download_first_pdf(pdf_candidates, pdf_path) if download_pdfs else ""
    if not pdf_source and pdf_path.exists():
        pdf_source = existing_metadata.get("pdf_source", "")
    has_local_pdf = pdf_path.exists()
    article_url = f"https://doi.org/{doi}"
    permalink = f"/publication/{slug}"
    excerpt = f"{journal}, {date[:4]}." if journal else date[:4]

    metadata = {
        "title": title,
        "collection": "publications",
        "category": "manuscripts",
        "orcid_sync": True,
        "source_orcid": ORCID_ID,
        "doi": doi,
        "work_type": work_type,
        "crossref_type": crossref_type,
        "first_author": first_author,
        "corresponding_author": corresponding_author,
        "featured": featured,
        "journal_impact_factor": metrics.get("impact_factor", 0),
        "impact_factor_year": metrics.get("impact_factor_year", ""),
        "impact_factor_source": metrics.get("impact_factor_source", ""),
        "permalink": permalink,
        "excerpt": excerpt,
        "date": date,
        "venue": journal,
        "authors": html_author_join(authors),
        "author_entries": author_entries(authors, doi),
        "originalurl": article_url,
        "link": article_url,
        "paperurl": f"/files/papers/{pdf_filename}" if has_local_pdf else False,
        "pdf_source": pdf_source if has_local_pdf else "",
        "citation": citation,
    }

    body = f"\n\nDOI: [{doi}](https://doi.org/{doi})\n"
    return {
        "filename": filename,
        "path": existing_publication.get("path") if existing_publication else OUTPUT_DIR / filename,
        "metadata": metadata,
        "body": body,
        "existing": existing_publication,
    }


def orcid_summaries() -> list[dict]:
    data = fetch_json(f"https://pub.orcid.org/v3.0/{ORCID_ID}/works")
    summaries = []
    skipped_counts: dict[str, int] = {}
    for group in data.get("group", []):
        work_summaries = group.get("work-summary", [])
        if work_summaries:
            summary = work_summaries[0]
            work_type = normalized_work_type(summary.get("type"))
            if is_journal_article_type(work_type, ALLOWED_ORCID_WORK_TYPES):
                summaries.append(summary)
            else:
                skipped_counts[work_type or "unknown"] = (
                    skipped_counts.get(work_type or "unknown", 0) + 1
                )
    if skipped_counts:
        skipped = ", ".join(
            f"{work_type}: {count}" for work_type, count in sorted(skipped_counts.items())
        )
        print(
            "Skipped ORCID works outside journal articles "
            f"({skipped}); conference/proceedings outputs are not synced.",
            file=sys.stderr,
        )
    return summaries


def is_generated_publication(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return "orcid_sync: true" in text


def publication_anchor(record: dict) -> str:
    return f"publication-publication-{record['path'].stem}"


def publication_news_label(date_value: str) -> str:
    try:
        return datetime.strptime(date_value[:10], "%Y-%m-%d").strftime("%Y-%m")
    except ValueError:
        return date_value[:7]


def is_recent_news_record(record: dict, *, current_year: int | None = None) -> bool:
    date_value = str(record.get("metadata", {}).get("date", ""))
    try:
        year = int(date_value[:4])
    except ValueError:
        return False
    if current_year is None:
        current_year = datetime.now().year
    return year >= current_year - RECENT_NEWS_YEAR_WINDOW


def publication_news_publication_meta(record: dict, anchor: str) -> str:
    metadata = record["metadata"]
    doi = str(metadata.get("doi", "")).lower()
    variable = NEWS_PUBLICATION_VARIABLES.get(doi)
    if variable:
        return (
            "{% include news-publication-meta.html "
            f'publication={variable} href="/publications/#{anchor}" %}}'
        )
    venue = html.escape(str(metadata.get("venue", "")))
    return f'<a href="/publications/#{anchor}"><em>{venue}</em></a>'


def liquid_string_value(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def publication_news_featured_suffix(record: dict, anchor: str) -> str:
    doi = str(record.get("metadata", {}).get("doi", "")).lower()
    media = NEWS_FEATURED_MEDIA.get(doi)
    if not media:
        return ""
    name = liquid_string_value(media["name"])
    logo = liquid_string_value(media["logo"])
    href = liquid_string_value(media.get("href") or f"/publications/#{anchor}")
    return (
        f'; featured in {{% include news-brand-logo.html name="{name}" '
        f'logo="{logo}" href="{href}" %}}'
    )


def publication_news_item(record: dict) -> str:
    metadata = record["metadata"]
    first_author = bool(metadata.get("first_author", False))
    css_class = "site-news__item site-news__item--key" if first_author else "site-news__item"
    role = "First-author paper" if first_author else "Co-author paper"
    date_label = publication_news_label(str(metadata.get("date", "")))
    anchor = publication_anchor(record)
    publication_meta = publication_news_publication_meta(record, anchor)
    featured_suffix = publication_news_featured_suffix(record, anchor)
    return (
        f'  <li class="{css_class}">{date_label}: <strong>{role}:</strong> '
        f"Published in {publication_meta}{featured_suffix}.</li>"
    )


def is_synced_publication_news_item(item: str) -> bool:
    return 'href="/publications/#publication-publication-' in item


def news_sort_key(item: str) -> tuple[datetime, str]:
    text = re.sub(r"<.*?>", "", item)
    month_match = re.search(r"(\d{4})-(\d{2}):", text)
    if month_match:
        try:
            return datetime(int(month_match.group(1)), int(month_match.group(2)), 1), text
        except ValueError:
            return datetime.min, text
    match = re.search(r"([A-Z][a-z]{2} \d{2}, \d{4}):", text)
    if not match:
        return datetime.min, text
    try:
        return datetime.strptime(match.group(1), "%b %d, %Y"), text
    except ValueError:
        return datetime.min, text


def sync_about_news(records: list[dict], *, dry_run: bool = False) -> bool:
    if not ABOUT_PAGE_PATH.exists():
        print(f"WARNING: About page not found; news was not updated: {ABOUT_PAGE_PATH}", file=sys.stderr)
        return False

    text = ABOUT_PAGE_PATH.read_text(encoding="utf-8")
    match = re.search(
        r"(?P<prefix>## News\s*\n\s*<ul class=\"site-news\">\s*\n)"
        r"(?P<body>.*?)"
        r"(?P<suffix>\s*</ul>)",
        text,
        flags=re.S,
    )
    if not match:
        print("WARNING: News list block was not found; news was not updated.", file=sys.stderr)
        return False

    existing_items = re.findall(r"\s*<li\b.*?</li>", match.group("body"), flags=re.S)
    kept_items = [
        "  " + item.strip()
        for item in existing_items
        if not is_synced_publication_news_item(item)
    ]
    publication_items = [
        publication_news_item(record)
        for record in records
        if record.get("metadata", {}).get("venue") and is_recent_news_record(record)
    ]
    merged_items = sorted(
        kept_items + publication_items,
        key=news_sort_key,
        reverse=True,
    )
    new_block = match.group("prefix") + "\n".join(merged_items) + match.group("suffix")
    new_text = text[: match.start()] + new_block + text[match.end() :]
    if new_text == text:
        return False
    if dry_run:
        print(f"Dry run: would update publication news entries in {ABOUT_PAGE_PATH}")
        return True
    ABOUT_PAGE_PATH.write_text(new_text, encoding="utf-8")
    print(f"Updated publication news entries in {ABOUT_PAGE_PATH}")
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and compare scholarly data without writing files.",
    )
    parser.add_argument(
        "--skip-news",
        action="store_true",
        help="Do not update publication news entries on the about page.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    global JOURNAL_METRICS
    JOURNAL_METRICS = load_journal_metrics()
    if not args.dry_run:
        OUTPUT_DIR.mkdir(exist_ok=True)
    existing_publications = load_existing_publications()
    records = [
        record
        for record in (
            publication_record(
                summary,
                existing_publications,
                download_pdfs=not args.dry_run,
            )
            for summary in orcid_summaries()
        )
        if record
    ]
    generated_paths = set()

    for record in sorted(records, key=lambda item: item["metadata"]["date"], reverse=True):
        path = record["path"]
        text = merge_existing_publication(
            record.get("existing"), record["metadata"], record["body"]
        )
        if args.dry_run:
            existing_text = path.read_text(encoding="utf-8") if path.exists() else ""
            if existing_text != text:
                print(f"Dry run: would write {path}")
        else:
            path.write_text(text, encoding="utf-8")
        generated_paths.add(path)

    for path in OUTPUT_DIR.glob("*.md"):
        if path not in generated_paths and is_generated_publication(path):
            if args.dry_run:
                print(f"Dry run: would remove {path}")
            else:
                path.unlink()

    if not args.skip_news:
        sync_about_news(
            sorted(records, key=lambda item: item["metadata"]["date"], reverse=True),
            dry_run=args.dry_run,
        )

    action = "Checked" if args.dry_run else "Synced"
    print(f"{action} {len(generated_paths)} ORCID journal articles for {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
