from common.db_util import fetch_all, is_db_configured
from common.settings import DB_FONT_STYLE_SQL

DEFAULT_FONT_STYLE_SQL = (
    "SELECT subtitle_name AS subtitleName, font_family_url AS fontFamilyUrl, "
    "CAST(font_size AS UNSIGNED) AS fontSize "
    "FROM subtitle "
    "WHERE type = 0 AND language = 'ZH' "
    "  AND subtitle_name IS NOT NULL AND font_family_url IS NOT NULL "
    "ORDER BY CAST(sort AS UNSIGNED), CAST(id AS UNSIGNED)"
)
DEFAULT_FONT_SIZE_SQL = (
    "SELECT CAST(font_size AS UNSIGNED) AS fontSize "
    "FROM subtitle "
    "WHERE type = 0 AND language = 'ZH' AND font_size IS NOT NULL "
    "ORDER BY CAST(sort AS UNSIGNED), CAST(id AS UNSIGNED) "
    "LIMIT 1"
)
DEFAULT_FONT_BOLD_SQL = (
    "SELECT CAST(font_bold AS UNSIGNED) AS fontBold "
    "FROM subtitle "
    "WHERE type = 0 AND language = 'ZH' AND font_bold IS NOT NULL "
    "ORDER BY CAST(sort AS UNSIGNED), CAST(id AS UNSIGNED) "
    "LIMIT 1"
)


def _safe_fetch_all(sql):
    if not sql:
        return []

    try:
        return fetch_all(sql)
    except Exception:
        return []


def _normalize_font_size(value):
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_font_bold(value):
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized_value = value.strip().lower()
        if normalized_value in ("1", "true"):
            return True
        if normalized_value in ("0", "false"):
            return False

    try:
        return bool(int(value))
    except (TypeError, ValueError):
        return None


def _normalize_font_style_row(row):
    subtitle_name = (
        row.get("subtitleName")
        or row.get("subtitle_name")
        or row.get("fontName")
        or row.get("font_name")
        or row.get("name")
    )
    font_family_url = (
        row.get("fontFamilyUrl")
        or row.get("font_family_url")
        or row.get("fontUrl")
        or row.get("font_url")
    )

    if not subtitle_name or not font_family_url:
        return None

    normalized_row = {
        "subtitleName": subtitle_name,
        "fontFamilyUrl": font_family_url,
    }
    font_size = _normalize_font_size(row.get("fontSize") or row.get("font_size"))
    if font_size is not None:
        normalized_row["fontSize"] = font_size

    return normalized_row


def load_font_style_cases(default_cases=None, sql=None):
    query_sql = sql or DB_FONT_STYLE_SQL or DEFAULT_FONT_STYLE_SQL
    if not is_db_configured() or not query_sql:
        return list(default_cases or [])

    rows = _safe_fetch_all(query_sql)
    font_cases = []
    for row in rows:
        normalized_row = _normalize_font_style_row(row)
        if normalized_row is not None:
            font_cases.append(normalized_row)

    return font_cases or list(default_cases or [])


def load_default_font_size(default_size=None, sql=None):
    if not is_db_configured():
        return default_size

    rows = _safe_fetch_all(sql or DEFAULT_FONT_SIZE_SQL)
    for row in rows:
        font_size = _normalize_font_size(row.get("fontSize") or row.get("font_size"))
        if font_size is not None:
            return font_size

    return default_size


def load_default_font_bold(default_bold=None, sql=None):
    if not is_db_configured():
        return default_bold

    rows = _safe_fetch_all(sql or DEFAULT_FONT_BOLD_SQL)
    for row in rows:
        font_bold = _normalize_font_bold(row.get("fontBold") or row.get("font_bold"))
        if font_bold is not None:
            return font_bold

    return default_bold
