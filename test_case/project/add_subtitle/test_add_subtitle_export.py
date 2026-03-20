import allure
import pytest

from api_moudle.project.add_subtitle.add_subtitle_export import ProjExport
from api_moudle.project.add_subtitle.add_subtitle_subtitle import ProjSubtitle
from api_moudle.project.home.proj_list import ProjList
from common.yaml_util import read_yaml, write_yaml


PROJECT_EXPORT_VERSION = 1
PROJECT_EXPORT_RESOLUTION = 1
PROJECT_EXPORT_DEVICE_TYPE = "desktop"


@allure.epic("AddSubtitle")
class TestProjExport:
    @staticmethod
    def _has_available_subtitles(project_id):
        subtitle_status, subtitle_data = ProjSubtitle().get_project_subtitle(project_id)
        return (
            subtitle_status == 200
            and subtitle_data.get("success") is True
            and bool(subtitle_data.get("data", {}).get("oriList"))
            and bool(subtitle_data.get("data", {}).get("transList"))
        )

    @staticmethod
    def _get_target_project_id():
        status_code, proj_data = ProjList().get_proj_list(pageSize=50)
        assert status_code == 200, f"failed to get project list: {proj_data}"
        rows = proj_data["data"]["rows"]
        assert rows

        for key in ("uploaded_video_project_id", "subtitle_project_id", "created_project_id", "test_project_id"):
            project_id = read_yaml(key, default=None)
            if project_id is None:
                continue
            for project in rows:
                if project["id"] == project_id and TestProjExport._has_available_subtitles(project_id):
                    return project_id

        for project in sorted(rows, key=lambda item: int(item["id"]), reverse=True):
            project_id = project["id"]
            if TestProjExport._has_available_subtitles(project_id):
                write_yaml({"subtitle_project_id": project_id})
                return project_id

        latest_project = max(rows, key=lambda project: int(project["id"]))
        return latest_project["id"]

    @allure.feature("Add Subtitle")
    @allure.story("Video Export")
    @allure.title("Export Project Video")
    @pytest.mark.P0
    def test_export_project_video(self):
        project_id = self._get_target_project_id()
        subtitle_api = ProjSubtitle()
        export_api = ProjExport()

        subtitle_status, subtitle_data = subtitle_api.wait_for_project_subtitle_ready(
            project_id,
            timeout=90,
            interval=3,
        )
        assert subtitle_status == 200
        assert subtitle_data["success"] is True

        export_subtitle_json = export_api.build_export_subtitle_json(subtitle_data)
        if not export_subtitle_json:
            pytest.skip("No exportable subtitle pairs were found for video export")

        session_status, session_id, session_data = export_api.get_project_session_id(project_id)
        assert session_status == 200, session_data
        assert session_id is not None

        export_status, export_data = export_api.export_backend(
            project_id,
            subtitle_json=export_subtitle_json,
            resolution=PROJECT_EXPORT_RESOLUTION,
            lip_sync=False,
            device_type=PROJECT_EXPORT_DEVICE_TYPE,
        )
        assert export_status == 200, export_data
        assert export_data["success"] is True
        if "code" in export_data:
            assert export_data["code"] == 0

        progress_status, progress_data = export_api.wait_for_export_completed(
            project_id,
            session_id=session_id,
            version=PROJECT_EXPORT_VERSION,
            timeout=900,
            interval=10,
        )
        assert progress_status == 200, progress_data
        assert progress_data["success"] is True
        assert export_api.normalize_export_progress(progress_data["data"]) == 100
