from __future__ import annotations

import csv
import hashlib
import html
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, quote


OUTPUT_DIR_NAME = "个人图片库"
IMAGE_DIR_NAME = "图片"
INDEX_FILE_NAME = "图片索引.html"

IMAGE_EXTENSIONS = {".gif", ".ico", ".jpeg", ".jpg", ".png", ".svg", ".webp"}
TEXT_EXTENSIONS = {
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".scss",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
SKIP_DIRS = {
    ".bundle",
    ".git",
    ".sass-cache",
    "_site",
    "__pycache__",
    "node_modules",
    "vendor",
}
SITE_IMAGE_DIRS = (
    "images",
    "files/papers/figures",
    "files/papers/videos/posters",
    "references",
)
IMAGE_URL_PATTERN = re.compile(
    r"""(?P<path>(?:/|(?:\.\./)*)(?:images|files/papers/figures|files/papers/videos/posters|references)/[^"'\s<>)\]}]+?\.(?:gif|ico|jpe?g|png|svg|webp))""",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ImageRecord:
    source_path: str
    source_file: Path
    copy_name: str
    category: str
    size_bytes: int
    sha256: str


def is_relative_to(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
    except ValueError:
        return False
    return True


def iter_files(root: Path, output_dir: Path, extensions: set[str]) -> list[Path]:
    files: list[Path] = []
    for current, dirs, names in os.walk(root):
        current_path = Path(current)
        dirs[:] = [
            name
            for name in dirs
            if name not in SKIP_DIRS
            and not is_relative_to(current_path / name, output_dir)
        ]
        for name in names:
            path = current_path / name
            if path.suffix.lower() in extensions:
                files.append(path)
    return files


def normalize_site_path(path: str) -> str:
    clean = unquote(path.split("#", 1)[0].split("?", 1)[0]).strip()
    while clean.startswith("../"):
        clean = clean[3:]
    return clean.lstrip("/")


def match_is_part_of_external_url(text: str, start: int) -> bool:
    prefix = text[:start]
    token_start = max(prefix.rfind(char) for char in " \t\r\n\"'(<") + 1
    return "://" in prefix[token_start:start]


def site_path_for_file(root: Path, path: Path) -> str:
    return "/" + path.relative_to(root).as_posix()


def collect_candidate_paths(root: Path, output_dir: Path) -> set[str]:
    paths: set[str] = set()

    for public_dir in SITE_IMAGE_DIRS:
        base = root / public_dir
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                paths.add(site_path_for_file(root, path))

    for text_file in iter_files(root, output_dir, TEXT_EXTENSIONS):
        text = text_file.read_text(encoding="utf-8", errors="ignore")
        for match in IMAGE_URL_PATTERN.finditer(text):
            if match_is_part_of_external_url(text, match.start()):
                continue
            paths.add("/" + normalize_site_path(match.group("path")))

    return paths


def image_category(source_path: str) -> str:
    if source_path.startswith("/references/"):
        return "source-screenshot"
    if source_path.startswith("/files/papers/videos/posters/"):
        return "video-poster"
    if source_path.startswith("/files/papers/figures/logos/"):
        return "journal-logo"
    if source_path.startswith("/files/papers/figures/"):
        return "publication-figure"
    if source_path.startswith("/images/logos/"):
        return "institution-logo"
    if source_path.startswith("/images/themes/"):
        return "theme-preview"
    if source_path.startswith("/images/favicon") or "touch-icon" in source_path:
        return "site-icon"
    if source_path in {"/images/profile.png", "/images/bio-photo.jpg", "/images/bio-photo-2.jpg"}:
        return "profile-photo"
    return "site-image"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_name_for_source(source_path: str, digest: str, used: set[str]) -> str:
    rel = source_path.lstrip("/")
    candidate = rel.replace("/", "__")
    if candidate not in used:
        used.add(candidate)
        return candidate

    stem = Path(candidate).stem
    suffix = Path(candidate).suffix
    candidate = f"{stem}__{digest[:8]}{suffix}"
    used.add(candidate)
    return candidate


def reset_generated_image_dir(output_dir: Path, image_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    if image_dir.exists():
        if not is_relative_to(image_dir, output_dir):
            raise RuntimeError(f"Refusing to clean unexpected path: {image_dir}")
        shutil.rmtree(image_dir)
    image_dir.mkdir(parents=True, exist_ok=True)


def build_records(root: Path, output_dir: Path) -> tuple[list[ImageRecord], list[str]]:
    image_dir = output_dir / IMAGE_DIR_NAME
    reset_generated_image_dir(output_dir, image_dir)

    records: list[ImageRecord] = []
    missing: list[str] = []
    used_names: set[str] = set()

    for source_path in sorted(collect_candidate_paths(root, output_dir), key=str.casefold):
        source_file = root / normalize_site_path(source_path)
        if not source_file.exists():
            missing.append(source_path)
            continue

        digest = sha256_file(source_file)
        copy_name = copy_name_for_source(source_path, digest, used_names)
        shutil.copy2(source_file, image_dir / copy_name)
        records.append(
            ImageRecord(
                source_path=source_path,
                source_file=source_file,
                copy_name=copy_name,
                category=image_category(source_path),
                size_bytes=source_file.stat().st_size,
                sha256=digest,
            )
        )

    return records, missing


def write_manifest(output_dir: Path, root: Path, records: list[ImageRecord]) -> None:
    manifest_path = output_dir / "manifest.csv"
    with manifest_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "copy_file",
                "site_path",
                "source_file",
                "category",
                "size_bytes",
                "sha256",
            ],
        )
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "copy_file": f"{IMAGE_DIR_NAME}/{record.copy_name}",
                    "site_path": record.source_path,
                    "source_file": record.source_file.relative_to(root).as_posix(),
                    "category": record.category,
                    "size_bytes": record.size_bytes,
                    "sha256": record.sha256,
                }
            )


def render_index(output_dir: Path, records: list[ImageRecord], missing: list[str]) -> None:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cards = []
    for record in records:
        image_href = f"{quote(IMAGE_DIR_NAME)}/{quote(record.copy_name)}"
        cards.append(
            f"""
      <figure class="image-card">
        <a href="{image_href}" target="_blank" rel="noopener">
          <img src="{image_href}" alt="{html.escape(record.source_path)}" loading="lazy">
        </a>
        <figcaption>
          <span class="category">{html.escape(record.category)}</span>
          <code>{html.escape(record.source_path)}</code>
          <span>{html.escape(record.copy_name)}</span>
        </figcaption>
      </figure>"""
        )

    missing_html = ""
    if missing:
        items = "\n".join(f"<li><code>{html.escape(path)}</code></li>" for path in missing)
        missing_html = f"""
    <section class="notice">
      <h2>Missing referenced files</h2>
      <ul>{items}</ul>
    </section>"""

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>网站图片个人库</title>
  <style>
    body {{
      margin: 0;
      background: #f6f7f9;
      color: #1f2933;
      font-family: "DejaVu Sans", "Segoe UI", sans-serif;
      font-size: 16px;
      line-height: 1.55;
    }}
    header {{
      padding: 28px clamp(18px, 4vw, 44px);
      background: #ffffff;
      border-bottom: 1px solid #d8dee9;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(28px, 4vw, 44px);
      line-height: 1.1;
    }}
    .summary {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px 20px;
      color: #52606d;
    }}
    main {{
      padding: 24px clamp(18px, 4vw, 44px) 44px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 18px;
    }}
    .image-card {{
      margin: 0;
      background: #ffffff;
      border: 1px solid #d8dee9;
      border-radius: 8px;
      overflow: hidden;
    }}
    .image-card a {{
      display: grid;
      place-items: center;
      min-height: 180px;
      background: #eef2f7;
    }}
    .image-card img {{
      display: block;
      width: 100%;
      height: 180px;
      object-fit: contain;
    }}
    figcaption {{
      display: grid;
      gap: 7px;
      padding: 12px;
      word-break: break-word;
    }}
    code {{
      font-family: "Cascadia Mono", "Consolas", monospace;
      font-size: 0.9em;
    }}
    .category {{
      width: max-content;
      max-width: 100%;
      padding: 2px 8px;
      border-radius: 999px;
      background: #e0f2f1;
      color: #00695c;
      font-weight: 700;
      font-size: 0.86em;
    }}
    .notice {{
      margin-bottom: 20px;
      padding: 14px 18px;
      border: 1px solid #f2c94c;
      background: #fff8db;
      border-radius: 8px;
    }}
  </style>
</head>
<body>
  <header>
    <h1>网站图片个人库</h1>
    <div class="summary">
      <span>生成时间：{html.escape(generated_at)}</span>
      <span>图片数量：{len(records)}</span>
      <span>清单：<a href="manifest.csv">manifest.csv</a></span>
    </div>
  </header>
  <main>
{missing_html}
    <section class="grid">
{''.join(cards)}
    </section>
  </main>
</body>
</html>
"""
    (output_dir / INDEX_FILE_NAME).write_text(html_text, encoding="utf-8")


def write_readme(output_dir: Path, records: list[ImageRecord]) -> None:
    text = (
        "网站图片个人库\n"
        "================\n\n"
        f"图片副本在 `{IMAGE_DIR_NAME}/`，共 {len(records)} 张。\n"
        f"双击 `{INDEX_FILE_NAME}` 可以用浏览器查看缩略图索引。\n"
        "`manifest.csv` 记录每张图片在网站里的原始路径和校验值。\n\n"
        "这个文件夹是自动生成的网站图片个人副本，可以随时重新生成；网站实际使用的原图仍保留在原来的公开路径。\n"
    )
    (output_dir / "README.txt").write_text(text, encoding="utf-8")


def configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    configure_console_encoding()
    root = Path(__file__).resolve().parents[1]
    output_dir = root / OUTPUT_DIR_NAME
    records, missing = build_records(root, output_dir)
    write_manifest(output_dir, root, records)
    render_index(output_dir, records, missing)
    write_readme(output_dir, records)

    print(f"Collected {len(records)} website images into: {output_dir}")
    print(f"Open: {output_dir / INDEX_FILE_NAME}")
    if missing:
        print(f"Warning: {len(missing)} referenced image paths were not found.")
    return 0 if not missing else 2


if __name__ == "__main__":
    raise SystemExit(main())
