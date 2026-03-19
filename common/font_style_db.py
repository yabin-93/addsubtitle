from common.db_util import fetch_all, is_db_configured
from common.settings import DB_FONT_STYLE_SQL


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

    return {
        "subtitleName": subtitle_name,
        "fontFamilyUrl": font_family_url,
    }


def load_font_style_cases(default_cases=None):
    if not is_db_configured() or not DB_FONT_STYLE_SQL:
        return list(default_cases or [])

    rows = fetch_all(DB_FONT_STYLE_SQL)
    font_cases = []
    for row in rows:
        normalized_row = _normalize_font_style_row(row)
        if normalized_row is not None:
            font_cases.append(normalized_row)

    return font_cases or list(default_cases or [])
