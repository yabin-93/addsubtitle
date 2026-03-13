import random
import time

import allure
import pytest

from api_moudle.project.home.proj_name_update import ProjUpdate
from api_moudle.project.home.proj_list import ProjList
from common.yaml_util import read_yaml, write_yaml


@allure.epic("addSubtitle")
class TestProjNameUpdate:
    @staticmethod
    def _get_target_project_id():
        for key in ("uploaded_video_project_id", "created_project_id", "test_project_id"):
            project_id = read_yaml(key, default=None)
            if project_id is not None:
                write_yaml({"test_project_id": project_id})
                return project_id

        pytest.skip("未找到 test_add_subtitle_create.py 创建的项目 id，请按回归顺序执行用例")

    @staticmethod
    def _wait_for_project_name(project_id, expected_name, timeout=30, interval=2):
        deadline = time.time() + timeout
        latest_project = None

        while time.time() < deadline:
            status_code, proj_data = ProjList().get_proj_list(pageSize=50)
            assert status_code == 200

            for project in proj_data["data"]["rows"]:
                if project["id"] == project_id:
                    latest_project = project
                    if project["name"] == expected_name:
                        return project
                    break

            time.sleep(interval)

        raise AssertionError(f"项目名称未更新为 {expected_name}, latest_project={latest_project}")

    @classmethod
    def setup_class(cls):
        cls.project_id = cls._get_target_project_id()

    @allure.feature("项目管理")
    @allure.story("修改项目名称")
    @allure.title("使用有效参数修改项目名称")
    @pytest.mark.P0
    def test_update_project_name_with_valid_params(self):
        new_name = f"Updated Project Name{random.randint(1, 100)}"

        status_code, data = ProjUpdate().update_project_name(self.project_id, new_name)

        assert status_code == 200
        assert data["success"] is True

        updated_project = self._wait_for_project_name(self.project_id, new_name)
        assert updated_project["name"] == new_name

    @allure.feature("项目管理")
    @allure.story("修改项目名称")
    @allure.title("使用无效项目ID修改项目名称")
    @pytest.mark.P0
    def test_update_project_name_with_invalid_id(self):
        status_code, data = ProjUpdate().update_project_name(9999999999999999, "Invalid Project Name")

        assert status_code == 500
        assert data.get("success") is False
        assert data["code"] == -33

    @allure.feature("项目管理")
    @allure.story("修改项目名称")
    @allure.title("使用空名称修改项目名称")
    @pytest.mark.skip(reason="非上线前回归用例，暂时跳过")
    def test_update_project_name_with_empty_name(self):
        status_code, data = ProjUpdate().update_project_name(self.project_id, "")

        assert status_code == 400 or data.get("success") is False

    @allure.feature("项目管理")
    @allure.story("修改项目名称")
    @allure.title("使用超长名称修改项目名称")
    @pytest.mark.skip(reason="非上线前回归用例，暂时跳过")
    def test_update_project_name_with_long_name(self):
        status_code, data = ProjUpdate().update_project_name(self.project_id, "A" * 256)

        assert status_code == 400 or data.get("success") is False
