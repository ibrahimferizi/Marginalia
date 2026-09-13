def parse_page_count(value):
    value = str(value or "").strip()
    if not value.isascii() or not value.isdecimal():
        return None
    count = int(value)
    return count if 0 < count <= 2147483647 else None


def source_metadata(record):
    work_id = str(record.get("work_id") or "").strip()
    return {
        "work_id": "" if work_id == "0" else work_id,
        "language_code": (record.get("language_code") or "").strip(),
        "source_format": (record.get("format") or "").strip(),
        "page_count": parse_page_count(record.get("num_pages")),
    }
