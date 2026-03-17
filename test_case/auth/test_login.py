import random

import allure
import pytest

from api_moudle.auth.login import Login
from common.settings import ADD_SUBTITLE_LOGIN_EMAIL
from common.yaml_util import read_yaml, write_yaml


@allure.epic("AddSubtitle")
class TestLogin:
    @allure.feature("用户登录")
    @allure.story("获取验证码")
    @allure.title("使用正确邮箱获取验证码")
    @pytest.mark.P0
    def test_input_correct_email(self):
        email = ADD_SUBTITLE_LOGIN_EMAIL
        status_code, data = Login().get_code(email)

        write_yaml({"code": data["data"]["code"]})
        assert status_code == 200
        assert data["code"] == 0
        assert data["msg"] == "success"

    @allure.feature("用户登录")
    @allure.story("获取验证码")
    @allure.title("使用错误格式邮箱获取验证码")
    @pytest.mark.skip(reason="非上线前回归用例，暂时跳过")
    def test_input_error_email(self):
        email = random.randint(1100000000, 9999999999)
        Login().get_code(email)

    @allure.feature("用户登录")
    @allure.story("用户登录验证")
    @allure.title("使用正确验证码登录")
    @pytest.mark.P0
    def test_right_code_login(self):
        code = read_yaml("code")
        status_code, data = Login().acc_pwd_login(code)
        # token = data["data"]["token"]
        # write_yaml({"cookie": f"talecast_token={token}"})

        assert status_code == 200
        assert data["msg"] == "success"
        assert data["success"] is True

    @allure.feature("用户登录")
    @allure.story("用户登录验证")
    @allure.title("使用错误验证码登录")
    @pytest.mark.P0
    def test_error_code_login(self):
        email = ADD_SUBTITLE_LOGIN_EMAIL
        Login().get_code(email)
        status_code, data = Login().acc_pwd_login("000000")

        assert status_code == 500
        assert data["success"] is False
        assert data["code"] == -3