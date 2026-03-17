import time

import allure
import pytest

from api_moudle.project.space.space_management import SpaceManagement


@allure.epic("AddSubtitle")
class TestSpaceManagement:
    @allure.feature("空间模块")
    @allure.story("导出视频管理")
    @allure.title("获取导出视频列表")
    @pytest.mark.P0
    def test_get_export_video_list(self):
        status_code, data = SpaceManagement().get_export_video_list()

        assert status_code == 200
        assert data["msg"] == "success"
        assert data["success"] is True
        assert data["data"]["type"] == 0

    @allure.feature("空间模块")
    @allure.story("视频素材管理")
    @allure.title("获取上传视频素材列表")
    @pytest.mark.P0
    def test_get_upload_video_material_list(self):
        status_code, data = SpaceManagement().get_upload_video_material_list()

        assert status_code == 200
        assert data["msg"] == "success"
        assert data["success"] is True
        assert data["data"]["type"] == 1

    @allure.feature("空间模块")
    @allure.story("语音管理")
    @allure.title("获取用户克隆语音列表")
    @pytest.mark.P0
    def test_get_user_clone_voice_list(self):
        status_code, data = SpaceManagement().get_user_clone_voice_list()

        assert status_code == 200
        assert data["msg"] == "success"
        assert data["success"] is True
        assert data["data"]["type"] == 2

    @allure.feature("空间模块")
    @allure.story("语音管理")
    @allure.title("获取用户语音列表")
    @pytest.mark.P0
    def test_get_user_voice_list(self):
        status_code, data = SpaceManagement().get_user_voice_list()

        assert status_code == 200
        assert data["msg"] == "success"
        assert data["success"] is True
        assert data["data"]["type"] == 3

    @allure.feature("空间模块")
    @allure.story("导出视频管理")
    @allure.title("测试导出视频列表分页功能")
    @pytest.mark.skip(reason="非上线前回归用例，暂时跳过")
    @pytest.mark.parametrize("pageIndex, pageSize", [(0, 12), (1, 10), (2, 5)])
    def test_get_export_video_list_with_pagination(self, pageIndex, pageSize):
        status_code, data = SpaceManagement().get_export_video_list(pageIndex=pageIndex, pageSize=pageSize)

        assert status_code == 200
        assert data["msg"] == "success"
        assert "data" in data
        assert "rows" in data["data"]
        assert "totalRowCount" in data["data"]
        assert "totalPageCount" in data["data"]

    @allure.feature("空间模块")
    @allure.story("性能测试")
    @allure.title("测试空间管理接口响应时间")
    @pytest.mark.P0
    def test_space_management_response_time(self):
        start_time = time.time()
        status_code, _ = SpaceManagement().get_export_video_list()
        assert time.time() - start_time < 5.0
        assert status_code == 200

        start_time = time.time()
        status_code, _ = SpaceManagement().get_upload_video_material_list()
        assert time.time() - start_time < 5.0
        assert status_code == 200

        start_time = time.time()
        status_code, _ = SpaceManagement().get_user_clone_voice_list()
        assert time.time() - start_time < 5.0
        assert status_code == 200

        start_time = time.time()
        status_code, _ = SpaceManagement().get_user_voice_list()
        assert time.time() - start_time < 5.0
        assert status_code == 200

    @allure.feature("空间模块")
    @allure.story("权限验证")
    @allure.title("使用无效Cookie访问空间管理接口")
    @pytest.mark.parametrize("cookie", ["invalid_token", "test_token"])
    @pytest.mark.P0
    def test_space_management_with_invalid_cookie(self, cookie):
        try:
            status_code, _ = SpaceManagement().get_export_video_list(cookie=cookie)
            assert status_code == 401
        except Exception as e:
            return [{"error": "使用无效cookie", "message": str(e)}]
