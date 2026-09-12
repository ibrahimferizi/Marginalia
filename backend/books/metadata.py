def source_metadata(record):
    work_id = str(record.get("work_id") or "").strip()
    return {
        "work_id": "" if work_id == "0" else work_id,
        "language_code": (record.get("language_code") or "").strip(),
        "source_format": (record.get("format") or "").strip(),
    }
