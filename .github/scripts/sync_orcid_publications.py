"""Sync ORCID works into Academic Pages publication markdown files."""

from __future__ import annotations

import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


ORCID_ID = "0000-0003-3088-2983"
AUTHOR_NAME = "Fan Cheng"
OUTPUT_DIR = Path("_publications")
PDF_DIR = Path("files/papers")
JOURNAL_METRICS_PATH = Path("_data/journal_metrics.json")
USER_AGENT = "fancheng5640.github.io ORCID sync (mailto:fancheng@mail.tau.ac.il)"


JOURNAL_METRICS = {
    "Nature Communications": {
        "impact_factor": 15.7,
        "impact_factor_year": 2024,
        "impact_factor_source": "https://www.nature.com/ncomms/journal-impact",
    },
    "Optica": {
        "impact_factor": 8.5,
        "impact_factor_year": 2024,
        "impact_factor_source": "https://opg.optica.org/optica/journal/optica/about.cfm",
    },
    "Photonics Research": {
        "impact_factor": 7.2,
        "impact_factor_year": 2024,
        "impact_factor_source": "https://opg.optica.org/prj/",
    },
    "Applied Physics Letters": {
        "impact_factor": 3.6,
        "impact_factor_year": 2024,
        "impact_factor_source": "https://pubs.aip.org/aip/apl/pages/about",
    },
    "Optics Express": {
        "impact_factor": 3.3,
        "impact_factor_year": 2024,
        "impact_factor_source": "https://opg.optica.org/oe/about",
    },
    "AIP Advances": {
        "impact_factor": 1.4,
        "impact_factor_year": 2024,
        "impact_factor_source": "https://pubs.aip.org/aip/adv/pages/about",
    },
}


# ORCID and Crossref do not reliably expose corresponding-author status.
# Add DOI keys here when a paper should be shown in the corresponding-author
# summary section.
ROLE_OVERRIDES = {
    # "10.0000/example": {"corresponding_author": True},
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
    return json.dumps(str(value), ensure_ascii=False)


def front_matter(metadata: dict) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {yaml_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def publication_record(summary: dict) -> dict | None:
    doi = doi_from_summary(summary)
    if not doi:
        return None
    title = summary["title"]["title"]["value"].strip()
    date = date_from_orcid(summary.get("publication-date"))
    journal = text_value(summary.get("journal-title"), "")

    try:
        crossref = fetch_crossref(doi)
        time.sleep(0.1)
    except (urllib.error.URLError, KeyError, TimeoutError) as exc:
        print(f"WARNING: Crossref lookup failed for {doi}: {exc}", file=sys.stderr)
        crossref = {}

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
    pdf_source = download_first_pdf(pdf_candidates, pdf_path)
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
        "originalurl": article_url,
        "link": article_url,
        "paperurl": f"/files/papers/{pdf_filename}" if has_local_pdf else False,
        "pdf_source": pdf_source if has_local_pdf else "",
        "citation": citation,
    }

    body = f"\n\nDOI: [{doi}](https://doi.org/{doi})\n"
    return {
        "filename": filename,
        "metadata": metadata,
        "body": body,
    }


def orcid_summaries() -> list[dict]:
    data = fetch_json(f"https://pub.orcid.org/v3.0/{ORCID_ID}/works")
    summaries = []
    for group in data.get("group", []):
        work_summaries = group.get("work-summary", [])
        if work_summaries:
            summaries.append(work_summaries[0])
    return summaries


def is_generated_publication(path: Path) -> bool:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    return "orcid_sync: true" in text


def main() -> int:
    global JOURNAL_METRICS
    JOURNAL_METRICS = load_journal_metrics()
    OUTPUT_DIR.mkdir(exist_ok=True)
    records = [
        record
        for record in (publication_record(summary) for summary in orcid_summaries())
        if record
    ]
    generated_paths = set()

    for record in sorted(records, key=lambda item: item["metadata"]["date"], reverse=True):
        path = OUTPUT_DIR / record["filename"]
        text = front_matter(record["metadata"]) + record["body"]
        path.write_text(text, encoding="utf-8")
        generated_paths.add(path)

    for path in OUTPUT_DIR.glob("*.md"):
        if path not in generated_paths and is_generated_publication(path):
            path.unlink()

    print(f"Synced {len(generated_paths)} ORCID publications into {OUTPUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
