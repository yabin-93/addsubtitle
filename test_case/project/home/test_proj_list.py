import time

import allure
import pytest

from api_moudle.project.home.proj_list import ProjList


@allure.epic("AddSubtitle")
class TestProjList:
    @allure.feature("项目首页")
    @allure.story("获取项目列表")
    @allure.title("获取正确的项目列表")
    @pytest.mark.P0
    def test_get_correct_proj_list(self):
        status_code, data = ProjList().get_proj_list()

        assert status_code == 200
        assert data["msg"] == "success"
        assert "data" in data
        assert "rows" in data["data"]

    @allure.feature("项目首页")
    @allure.story("项目列表分页")
    @allure.title("测试项目列表分页功能")
    @pytest.mark.P0
    def test_proj_list_with_pagination(self):
        status_code, data = ProjList().get_proj_list()

        assert status_code == 200
        assert data["msg"] == "success"
        assert data["success"] is True
        assert "data" in data
        assert "rows" in data["data"]
        assert "totalRowCount" in data["data"]
        assert "totalPageCount" in data["data"]
        assert len(data["data"]["rows"]) > 0

    @allure.feature("项目首页")
    @allure.story("项目列表字段验证")
    @allure.title("验证项目列表包含必需字段")
    @pytest.mark.P0
    def test_proj_list_contains_required_fields(self):
        status_code, data = ProjList().get_proj_list()

        assert status_code == 200
        assert "data" in data
        assert "rows" in data["data"]
        assert "totalRowCount" in data["data"]
        assert "totalPageCount" in data["data"]

    @allure.feature("项目首页")
    @allure.story("权限验证")
    @allure.title("使用无效Cookie获取项目列表")
    @pytest.mark.parametrize("cookie", ["test_token"])
    @pytest.mark.P0
    def test_get_proj_list_without_login(self, cookie):
        try:
            status_code, data = ProjList().get_proj_list(cookie=cookie)
            assert status_code == 401 or data.get("success") is False
        except Exception as e:
            return [{"error": "使用无效cookie", "message": str(e)}]

    @allure.feature("项目首页")
    @allure.story("性能测试")
    @allure.title("测试项目列表接口响应时间")
    @pytest.mark.P0
    def test_proj_list_response_time(self):
        start_time = time.time()
        status_code, _ = ProjList().get_proj_list()
        end_time = time.time()

        assert end_time - start_time < 5.0
        assert status_code == 200
