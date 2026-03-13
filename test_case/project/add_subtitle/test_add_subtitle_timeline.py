import allure
import pytest

from api_moudle.project.add_subtitle.add_subtitle_create import ProjCreate
from api_moudle.project.home.proj_list import ProjList
from api_moudle.project.add_subtitle.add_subtitle_timeline import Timeline
from common.yaml_util import read_yaml, write_yaml


@allure.epic("addSubtitle")
class TestTimeline:
    @staticmethod
    def _is_available_timeline_project(project_id):
        timeline_api = Timeline()
        source_status, source_data = timeline_api.get_project_source(project_id)
        detail_status, detail_data = ProjCreate().get_project_detail(project_id)
        return (
            source_status == 200
            and detail_status == 200
            and source_data.get("success") is True
            and detail_data.get("success") is True
            and timeline_api.find_video_detail(source_data) is not None
        )

    @staticmethod
    def _get_target_project_id():
        status_code, proj_data = ProjList().get_proj_list(pageSize=50)
        assert status_code == 200
        rows = proj_data["data"]["rows"]
        assert rows

        # 优先使用最新创建的项目 id。
        for key in ("created_project_id", "uploaded_video_project_id", "timeline_project_id", "test_project_id"):
            project_id = read_yaml(key, default=None)
            if project_id is None:
                continue
            for project in rows:
                if project["id"] == project_id and TestTimeline._is_available_timeline_project(project_id):
                    write_yaml({"timeline_project_id": project_id})
                    return project_id

        for project in sorted(rows, key=lambda item: int(item["id"]), reverse=True):
            project_id = project["id"]
            if TestTimeline._is_available_timeline_project(project_id):
                write_yaml({"timeline_project_id": project_id})
                return project_id

        latest_project = max(rows, key=lambda project: int(project["id"]))
        return latest_project["id"]

    @allure.feature("时间轴模块")
    @allure.story("时间轴")
    @allure.title("视频开关功能-正常场景")
    @pytest.mark.P0
    def test_update_video_visible_toggle(self):
        project_id = self._get_target_project_id()
        timeline_api = Timeline()

        source_status, source_data = timeline_api.get_project_source(project_id)
        assert source_status == 200
        assert source_data["success"] is True

        original_video_detail = timeline_api.find_video_detail(source_data)
        assert original_video_detail is not None
        original_video_detail = dict(original_video_detail)
        original_visible = original_video_detail["hideOrMute"]
        latest_video_detail = dict(original_video_detail)

        try:
            close_item = timeline_api.build_update_video_item(latest_video_detail, visible=False)
            close_status, close_data = timeline_api.update_video(project_id, video_list=[close_item])
            assert close_status == 200
            assert close_data["success"] is True
            assert close_data["code"] == 0

            closed_status, closed_data = timeline_api.wait_for_video_visible_updated(
                project_id,
                visible=False,
                video_id=original_video_detail["id"],
                timeout=30,
                interval=2,
            )
            assert closed_status == 200
            assert closed_data["success"] is True

            latest_video_detail = timeline_api.find_video_detail(closed_data, video_id=original_video_detail["id"])
            assert latest_video_detail is not None
            assert latest_video_detail["hideOrMute"] is False

            open_item = timeline_api.build_update_video_item(latest_video_detail, visible=True)
            open_status, open_data = timeline_api.update_video(project_id, video_list=[open_item])
            assert open_status == 200
            assert open_data["success"] is True
            assert open_data["code"] == 0

            opened_status, opened_data = timeline_api.wait_for_video_visible_updated(
                project_id,
                visible=True,
                video_id=original_video_detail["id"],
                timeout=30,
                interval=2,
            )
            assert opened_status == 200
            assert opened_data["success"] is True

            latest_video_detail = timeline_api.find_video_detail(opened_data, video_id=original_video_detail["id"])
            assert latest_video_detail is not None
            assert latest_video_detail["hideOrMute"] is True
        finally:
            restore_item = timeline_api.build_update_video_item(latest_video_detail, visible=original_visible)
            restore_status, restore_data = timeline_api.update_video(project_id, video_list=[restore_item])
            assert restore_status == 200
            assert restore_data["success"] is True

            restored_status, restored_data = timeline_api.wait_for_video_visible_updated(
                project_id,
                visible=original_visible,
                video_id=original_video_detail["id"],
                timeout=30,
                interval=2,
            )
            assert restored_status == 200
            assert restored_data["success"] is True
