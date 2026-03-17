import os


def _get_env(name, default=None):
    value = os.getenv(name)
    if value is None:
        return default

    value = value.strip()
    return value or default


ADD_SUBTITLE_BASE_URL = _get_env("ADD_SUBTITLE_BASE_URL", "https://staging.addsubtitle.ai").rstrip("/")
ADD_SUBTITLE_LOGIN_EMAIL = _get_env("ADD_SUBTITLE_LOGIN_EMAIL", "19349490@qq.com")
