import requests

from common.logger import logger
from common.yaml_util import read_yaml, write_yaml


BASE_URL = "https://staging.addsubtitle.ai"
DEFAULT_LOGIN_EMAIL = "1020817070@qq.com"


def _parse_response(response):
    try:
        return response.json()
    except Exception:
        return {"raw": response.text}


def refresh_cookie(email=None):
    email = email or read_yaml("email", default=DEFAULT_LOGIN_EMAIL)
    logger.info(f"开始刷新登录态，邮箱: {email}")

    code_resp = requests.post(
        BASE_URL + "/api/auth/email-verification-code",
        json={"email": email, "language": "en"},
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    code_data = _parse_response(code_resp)
    if code_resp.status_code != 200 or code_data.get("success") is not True:
        raise RuntimeError(f"获取验证码失败: status={code_resp.status_code}, data={code_data}")

    code = code_data["data"]["code"]

    login_resp = requests.post(
        BASE_URL + "/api/auth/newLogin",
        json={
            "email": email,
            "captchaCode": code,
            "recall": None,
            "language": "English",
            "invitationCode": None,
        },
        headers={"Content-Type": "application/json"},
        timeout=20,
    )
    login_data = _parse_response(login_resp)
    if login_resp.status_code != 200 or login_data.get("success") is not True:
        raise RuntimeError(f"登录失败: status={login_resp.status_code}, data={login_data}")

    token = login_data["data"]["token"]
    cookie = f"talecast_token={token}"
    write_yaml({"email": email, "code": code, "token": token, "cookie": cookie})
    logger.info("登录态刷新成功")
    return cookie


def get_cookie(force_refresh=False):
    if not force_refresh:
        cookie = read_yaml("cookie", default=None)
        if cookie:
            return cookie
    return refresh_cookie()
