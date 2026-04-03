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

    @classmethod
    def _prepare_export_context(cls, require_export_payload=True):
        project_id = cls._get_target_project_id()
        subtitle_api = ProjSubtitle()
        export_api = ProjExport()

        subtitle_status, subtitle_data = subtitle_api.wait_for_project_subtitle_ready(
            project_id,
            timeout=90,
            interval=3,
        )
        assert subtitle_status == 200
        assert subtitle_data["success"] is True

        export_subtitle_json = None
        if require_export_payload:
            export_subtitle_json = export_api.build_export_subtitle_json(subtitle_data)
            if not export_subtitle_json:
                pytest.skip("No exportable subtitle pairs were found for video export")

        session_status, session_id, session_data = export_api.get_project_session_id(project_id)
        assert session_status == 200, session_data
        assert session_id is not None

        return project_id, export_api, export_subtitle_json, session_id

    @staticmethod
    def _assert_success_response(status_code, data, label):
        assert status_code == 200, f"{label} failed: {data}"
        if isinstance(data, dict):
            if "success" in data:
                assert data["success"] is True, f"{label} failed: {data}"
            if "code" in data:
                assert data["code"] == 0, f"{label} failed: {data}"

    @classmethod
    def _assert_export_completed(cls, export_api, project_id, session_id, export_status, export_data):
        cls._assert_success_response(export_status, export_data, "export_backend")

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

    @allure.feature("Add Subtitle")
    @allure.story("Backend Video Export")
    @allure.title("Export Project Video")
    @pytest.mark.P0
    def test_export_project_video(self):
        project_id, export_api, export_subtitle_json, session_id = self._prepare_export_context()

        export_status, export_data = export_api.export_backend(
            project_id,
            subtitle_json=export_subtitle_json,
            resolution=PROJECT_EXPORT_RESOLUTION,
            lip_sync=False,
            device_type=PROJECT_EXPORT_DEVICE_TYPE,
        )
        self._assert_export_completed(
            export_api,
            project_id,
            session_id,
            export_status,
            export_data,
        )

    @allure.feature("Add Subtitle")
    @allure.story("Frontend Video Export")
    @allure.title("Export Project Video On Frontend")
    @pytest.mark.P0
    def test_export_project_video_on_frontend(self):
        project_id, export_api, _, session_id = self._prepare_export_context(require_export_payload=False)

        export_status, export_data = export_api.export_frontend(
            project_id,
            session_id=session_id,
        )
        assert export_status == 200, export_data
        assert export_data["sessionId"] == session_id

        project_point = export_data.get("projectPoint", {})
        self._assert_success_response(
            project_point.get("status_code"),
            project_point.get("data"),
            "projectPoint",
        )

        event_conform = export_data.get("eventConform", {})
        self._assert_success_response(
            event_conform.get("status_code"),
            event_conform.get("data"),
            "eventConform",
        )

        export_front = export_data.get("exportFront", {})
        self._assert_success_response(
            export_front.get("status_code"),
            export_front.get("data"),
            "exportFront",
        )
