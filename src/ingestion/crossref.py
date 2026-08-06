from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import requests

# Tự động thêm 'src' vào sys.path nếu chưa có để cho phép chạy script trực tiếp
_src_dir = Path(__file__).resolve().parent.parent
if str(_src_dir) not in sys.path:
    sys.path.insert(0, str(_src_dir))

from core.config import Settings

logger = logging.getLogger(__name__)

# Crossref public REST API endpoint
CROSSREF_API_URL = "https://api.crossref.org/works"

# User-Agent: Crossref khuyến khích ghi thông tin liên hệ để ưu tiên rate limit
_USER_AGENT = "DataObservabilityLab/1.0 (mailto:student@example.com)"


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str          # DOI
    title: str
    summary: str           # abstract
    authors: list[str]
    categories: list[str]  # subject areas
    primary_category: str
    published: str         # ISO date string, e.g. "2024-03-15"
    updated: str           # deposited/indexed date
    abs_url: str           # DOI URL
    pdf_url: str           # link to PDF nếu có
    comment: str           # type of work, e.g. "journal-article"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_date(date_obj: dict | None) -> str:
    """Chuyển Crossref date-parts object thành ISO date string."""
    if not date_obj:
        return ""
    parts = date_obj.get("date-parts", [[]])
    if not parts or not parts[0]:
        return ""
    components = parts[0]
    try:
        year = int(components[0]) if len(components) > 0 else 0
        month = int(components[1]) if len(components) > 1 else 1
        day = int(components[2]) if len(components) > 2 else 1
        return f"{year:04d}-{month:02d}-{day:02d}"
    except (TypeError, ValueError):
        return ""


def _extract_pdf_url(links: list[dict] | None) -> str:
    """Trích PDF URL từ danh sách link objects."""
    if not links:
        return ""
    for link in links:
        content_type = link.get("content-type", "")
        if "pdf" in content_type.lower():
            return link.get("URL", "")
    return ""


def _strip_html(text: str) -> str:
    """Bỏ các thẻ HTML đơn giản trong abstract từ Crossref."""
    import re
    return re.sub(r"<[^>]+>", "", text).strip()


# ---------------------------------------------------------------------------
# parse_crossref_payload
# ---------------------------------------------------------------------------

def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API payload thành list PaperRecord.

    Steps:
    1. Duyệt ``payload["message"]["items"]``.
    2. Lấy DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuẩn hoá text và bỏ record không hợp lệ:
       - Thiếu DOI → bỏ
       - Thiếu title → bỏ
       - Thiếu abstract/description (sau khi strip HTML) → bỏ
    4. Trả về list ``PaperRecord``.
    """
    items: list[dict] = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    skipped_no_doi = skipped_no_title = skipped_no_abstract = 0

    for item in items:
        # --- paper_id: DOI ---
        doi = (item.get("DOI") or "").strip()
        if not doi:
            skipped_no_doi += 1
            logger.debug("Bỏ qua item thiếu DOI: %s", item.get("title"))
            continue

        # --- title (bắt buộc) ---
        title_list = item.get("title") or []
        title = title_list[0].strip() if title_list else ""
        if not title:
            skipped_no_title += 1
            logger.debug("Bỏ qua item thiếu title: DOI=%s", doi)
            continue

        # --- abstract / summary (bắt buộc) ---
        # Crossref có thể trả về `abstract` hoặc `description` tuỳ publisher
        raw_abstract = item.get("abstract") or item.get("description") or ""
        summary = _strip_html(raw_abstract)
        if not summary:
            skipped_no_abstract += 1
            logger.debug("Bỏ qua item thiếu abstract: DOI=%s | title=%s", doi, title[:60])
            continue

        # --- authors ---
        raw_authors = item.get("author") or []
        authors: list[str] = []
        for a in raw_authors:
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            if family:
                name = f"{given} {family}".strip() if given else family
            else:
                name = a.get("name", "").strip()
            if name:
                authors.append(name)

        # --- categories / subject ---
        categories: list[str] = [s.strip() for s in (item.get("subject") or []) if s.strip()]
        primary_category = categories[0] if categories else ""

        # --- dates ---
        published_date = (
            _extract_date(item.get("published"))
            or _extract_date(item.get("published-online"))
            or _extract_date(item.get("published-print"))
            or _extract_date(item.get("issued"))
            or _extract_date(item.get("created"))
        )
        updated_date = (
            _extract_date(item.get("deposited"))
            or _extract_date(item.get("indexed"))
        )

        # --- URLs ---
        abs_url = item.get("URL") or f"https://doi.org/{doi}"
        pdf_url = _extract_pdf_url(item.get("link"))

        # --- comment: loại tài liệu ---
        comment = item.get("type", "")

        record = PaperRecord(
            paper_id=doi,
            title=title,
            summary=summary,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published_date,
            updated=updated_date,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )
        records.append(record)

    logger.info(
        "Parsed %d/%d items thành công (bỏ: %d no-DOI, %d no-title, %d no-abstract).",
        len(records),
        len(items),
        skipped_no_doi,
        skipped_no_title,
        skipped_no_abstract,
    )
    return records


# ---------------------------------------------------------------------------
# fetch_source_records
# ---------------------------------------------------------------------------

def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Gọi Crossref API, lưu raw response, parse thành records.

    Steps:
    1. Tạo params từ settings.source_query, settings.source_filter, settings.max_results.
    2. Gọi API với retry cho các status code 429/503 (exponential back-off).
    3. Lưu raw response vào settings.paths.raw_api_response.
    4. Parse payload bằng parse_crossref_payload.
    5. Lưu records vào settings.paths.raw_records_json.
    """
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
        "select": (
            "DOI,title,abstract,author,subject,"
            "published,published-online,published-print,issued,created,deposited,indexed,"
            "URL,link,type"
        ),
    }
    headers = {"User-Agent": _USER_AGENT}

    # --- Retry logic ---
    max_retries = 5
    retry_delays = [2, 5, 10, 30, 60]  # giây, exponential-like
    response: requests.Response | None = None

    for attempt in range(max_retries):
        try:
            logger.info(
                "Gọi Crossref API (attempt %d/%d): query=%r",
                attempt + 1,
                max_retries,
                settings.source_query,
            )
            response = requests.get(
                CROSSREF_API_URL,
                params=params,
                headers=headers,
                timeout=30,
            )
            if response.status_code in (429, 503):
                wait = retry_delays[min(attempt, len(retry_delays) - 1)]
                logger.warning(
                    "HTTP %d – sẽ thử lại sau %ds...", response.status_code, wait
                )
                time.sleep(wait)
                continue
            response.raise_for_status()
            break  # thành công
        except requests.RequestException as exc:
            if attempt < max_retries - 1:
                wait = retry_delays[min(attempt, len(retry_delays) - 1)]
                logger.warning("Request lỗi (%s) – thử lại sau %ds...", exc, wait)
                time.sleep(wait)
            else:
                raise

    if response is None or not response.ok:
        raise RuntimeError(
            f"Không thể lấy dữ liệu từ Crossref sau {max_retries} lần thử."
        )

    payload: dict = response.json()

    # --- Lưu raw API response ---
    raw_response_path: Path = settings.paths.raw_api_response
    raw_response_path.parent.mkdir(parents=True, exist_ok=True)
    raw_response_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("Đã lưu raw API response → %s", raw_response_path)

    # --- Parse ---
    records = parse_crossref_payload(payload)

    # --- Lưu parsed records ---
    raw_records_path: Path = settings.paths.raw_records_json
    raw_records_path.parent.mkdir(parents=True, exist_ok=True)
    raw_records_path.write_text(
        json.dumps([asdict(r) for r in records], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(
        "Đã lưu %d parsed records → %s", len(records), raw_records_path
    )

    return records


# ---------------------------------------------------------------------------
# load_raw_records
# ---------------------------------------------------------------------------

def load_raw_records(path: Path) -> list[PaperRecord]:
    """Đọc JSON snapshot đã lưu và map thành list PaperRecord."""
    data = json.loads(path.read_text(encoding="utf-8"))
    records = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=item.get("paper_id", ""),
                title=item.get("title", ""),
                summary=item.get("summary", ""),
                authors=item.get("authors", []),
                categories=item.get("categories", []),
                primary_category=item.get("primary_category", ""),
                published=item.get("published", ""),
                updated=item.get("updated", ""),
                abs_url=item.get("abs_url", ""),
                pdf_url=item.get("pdf_url", ""),
                comment=item.get("comment", ""),
            )
        )
    logger.info("Đã load %d records từ %s", len(records), path)
    return records


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from core.config import load_settings

    settings = load_settings()
    logger.info("Chạy fetch_source_records từ main script...")
    records = fetch_source_records(settings)
    print(f"\nSuccessfully fetched and parsed {len(records)} paper records.")
    if records:
        sample = records[0]
        print(f"Sample record:")
        print(f"  - DOI      : {sample.paper_id}")
        print(f"  - Title    : {sample.title}")
        print(f"  - Authors  : {', '.join(sample.authors[:3])}")
        print(f"  - Published: {sample.published}")
        print(f"  - Abstract : {sample.summary[:120]}...")

