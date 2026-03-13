import allure
import pytest

from api_moudle.project.add_subtitle.add_subtitle_create import ProjCreate


@allure.epic("addSubtitle")
class TestProjCreate:
    @allure.feature("项目管理")
    @allure.story("上传项目视频")
    @allure.title("创建项目后上传默认视频")
    @pytest.mark.P0
    def test_create_project_and_upload_default_video(self):
        api = ProjCreate()
        video_path = api.get_default_video_path()
        if not video_path.exists():
            pytest.skip(f"default video file not found: {video_path}")

        project_name = video_path.stem
        status_code, flow_data = api.create_project_flow(video_path=video_path)
        assert status_code == 200
        assert flow_data["create"]["success"] is True
        assert flow_data["projectName"] == project_name
        assert flow_data["editingEvents"]["project_edit"]["data"]["success"] is True
        assert flow_data["editingEvents"]["loading_start"]["data"]["success"] is True
        assert flow_data["uploadVideo"]["complete"]["success"] is True
        assert flow_data["uploadThumbnail"]["complete"]["success"] is True
        assert flow_data["uploadAudio"]["complete"]["success"] is True
        assert len(flow_data["uploadVideo"]["completedParts"]) == api.get_upload_part_count(video_path.stat().st_size)
        assert flow_data["projectReady"]["detail"]["data"]["data"]["thumbnail"].endswith(".png")
        assert flow_data["projectReady"]["resources"]["video_url"].endswith(".mp4")
        assert flow_data["projectReady"]["resources"]["sprite_url"].endswith(".jpg")

        project_id = flow_data["projectId"]
        ready_status, ready_data = api.wait_for_project_media_ready(project_id, require_thumbnail=True, timeout=30, interval=2)
        assert ready_status == 200
        assert ready_data["status"]["data"]["data"]["projectId"] == project_id
        assert ready_data["status"]["data"]["data"]["videoUpload"] is True
        assert ready_data["status"]["data"]["data"]["videoCompleted"] is True
        assert ready_data["source"]["data"]["data"]["video"]["projectId"] == project_id
        assert ready_data["source"]["data"]["data"]["video"]["url"].endswith(".mp4")

        detail_status, detail_data = api.get_project_detail(project_id)
        assert detail_status == 200
        assert detail_data["success"] is True
        assert detail_data["data"]["name"] == project_name
