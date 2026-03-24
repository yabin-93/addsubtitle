from api_moudle.project.home.base_api import BaseApi
from common.logger import logger
from common.settings import ADD_SUBTITLE_LOGIN_EMAIL
from common.yaml_util import read_yaml, write_yaml


class Login(BaseApi):
    # 获取邮箱验证码，供后续验证码登录使用。
    def get_code(self, email):
        try:
            logger.info(f"开始获取验证码，邮箱: {email}")
            res = self.run_request("auth/login.yaml", "get_code", email=email)
            if res[0] == 200 and res[1].get("success") is True:
                # 测试环境会直接返回验证码，供下一步登录复用。
                code = res[1]["data"]["code"]
                write_yaml({"email": email, "code": code})
                self.code = code
            return res
        except Exception as e:
            logger.error(f"获取验证码失败，邮箱: {email}，错误: {e}")
            return [None, {"error": "get_code_failed", "message": str(e)}]

    # 使用邮箱和验证码登录，并把 token/cookie 持久化到本地 YAML。
    def acc_pwd_login(self, code, email=None):
        login_email = email or read_yaml("email", default=ADD_SUBTITLE_LOGIN_EMAIL)
        try:
            res = self.run_request("auth/login.yaml", "acc_pwd_login", code=code, email=login_email)
            if res[0] == 200 and res[1].get("success") is True:
                # 后续业务接口统一通过 Cookie 中的 talecast_token 复用登录态。
                token = res[1]["data"]["token"]
                write_yaml({"email": login_email, "code": code, "token": token, "cookie": f"talecast_token={token}"})
            return res
        except Exception as e:
            logger.error(f"登录失败，错误: {e}")
            return [None, {"error": "acc_pwd_login_failed", "message": str(e)}]


if __name__ == "__main__":
    login = Login()
    _, data = login.get_code(ADD_SUBTITLE_LOGIN_EMAIL)
    print(login.acc_pwd_login(data["data"]["code"], email=ADD_SUBTITLE_LOGIN_EMAIL))
