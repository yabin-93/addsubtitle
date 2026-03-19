from common.db_util import fetch_all, is_db_configured


DEFAULT_BACKGROUND_SQL = (
    "SELECT "
    "CAST(id AS UNSIGNED) AS id, "
    "bg_name AS bgName, "
    "bg_url AS bgUrl, "
    "preview_img_url AS previewImgUrl "
    "FROM background "
    "WHERE id IS NOT NULL "
    "ORDER BY CAST(id AS UNSIGNED)"
)


def _safe_fetch_all(sql):
    if not sql:
        return []

    try:
        return fetch_all(sql)
    except Exception:
        return []


def _normalize_background_id(value):
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_text(value):
    if value is None:
        return None
    return str(value).strip() or None


def _normalize_background_row(row):
    background_id = _normalize_background_id(row.get("id") or row.get("backgroundId"))
    if background_id is None:
        return None

    normalized_row = {
        "id": background_id,
        "bgName": _normalize_text(row.get("bgName") or row.get("bg_name")),
        "bgUrl": _normalize_text(row.get("bgUrl") or row.get("bg_url")),
        "previewImgUrl": _normalize_text(row.get("previewImgUrl") or row.get("preview_img_url")),
    }
    return normalized_row


def load_background_cases(default_cases=None, sql=None):
    if not is_db_configured():
        return list(default_cases or [])

    rows = _safe_fetch_all(sql or DEFAULT_BACKGROUND_SQL)
    background_cases = []
    for row in rows:
        normalized_row = _normalize_background_row(row)
        if normalized_row is not None:
            background_cases.append(normalized_row)

    return background_cases or list(default_cases or [])
