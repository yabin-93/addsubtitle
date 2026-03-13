from api_moudle.base_api import BaseApi
from common.logger import logger
from common.yaml_util import write_yaml


class Login(BaseApi):
    def get_code(self, email):
        try:
            logger.info(f"开始获取验证码，邮箱: {email}")
            res = self.run_request("login.yaml", "get_code", email=email)
            if res[0] == 200 and res[1].get("success") is True:
                # 测试环境会直接返回验证码，供下一步登录复用。
                code = res[1]["data"]["code"]
                write_yaml({"email": email, "code": code})
                self.code = code
            return res
        except Exception as e:
            logger.error(f"获取验证码失败，邮箱: {email}，错误: {e}")
            return [None, {"error": "get_code_failed", "message": str(e)}]

    def acc_pwd_login(self, code):
        try:
            res = self.run_request("login.yaml", "acc_pwd_login", code=code)
            if res[0] == 200 and res[1].get("success") is True:
                # 后续业务接口统一通过 Cookie 中的 talecast_token 复用登录态。
                token = res[1]["data"]["token"]
                write_yaml({"code": code, "token": token, "cookie": f"talecast_token={token}"})
            return res
        except Exception as e:
            logger.error(f"登录失败，错误: {e}")
            return [None, {"error": "acc_pwd_login_failed", "message": str(e)}]


if __name__ == "__main__":
    login = Login()
    _, data = login.get_code("1020817070@qq.com")
    print(login.acc_pwd_login(data["data"]["code"]))
