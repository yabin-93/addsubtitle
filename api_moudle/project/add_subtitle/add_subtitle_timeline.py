import time

from api_moudle.project.home.base_api import BaseApi
from api_moudle.project.add_subtitle.add_subtitle_create import ProjCreate
from common.logger import logger


class Timeline(BaseApi):
    @staticmethod
    def find_video_detail(source_data, video_id=0):
        data = source_data.get("data", {}) if isinstance(source_data, dict) else {}
        video_details = data.get("video", {}).get("videoDetails", [])
        for video_detail in video_details:
            if video_id is None or video_detail.get("id") == video_id:
                return video_detail
        return None

    @staticmethod
    def normalize_track_index(track_index):
        if isinstance(track_index, float) and track_index.is_integer():
            return int(track_index)
        return track_index

    @classmethod
    def build_update_video_item(cls, video_detail, visible):
        return {
            "id": video_detail.get("id", 0),
            "volume": video_detail.get("volume", 1),
            "startTime": video_detail.get("startTime", 0),
            "offset": video_detail.get("offset", 0),
            "trackOffset": video_detail.get("trackOffset", 0),
            "duration": video_detail.get("duration", 0),
            "materialDuration": video_detail.get("materialDuration", video_detail.get("duration", 0)),
            "hideOrMute": visible,
            "trackIndex": cls.normalize_track_index(video_detail.get("trackIndex", 0)),
            "type": "video",
            "visible": visible,
        }

    def get_project_session_id(self, project_id, cookie=None):
        detail_status, detail_data = ProjCreate().get_project_detail(project_id, cookie=cookie)
        if detail_status != 200 or detail_data.get("success") is not True:
            return [detail_status, None, detail_data]

        session_id = detail_data.get("data", {}).get("sessionId")
        if not session_id:
            return [
                None,
                None,
                {
                    "error": "project_session_id_not_found",
                    "message": "未获取到项目 sessionId",
                    "data": detail_data,
                },
            ]

        return [200, session_id, detail_data]

    def get_project_source(self, project_id, cookie=None):
        return ProjCreate().get_project_source(project_id, cookie=cookie)

    def update_video(self, project_id, video_list, session_id=None, cookie=None):
        try:
            if session_id is None:
                session_status, session_id, session_data = self.get_project_session_id(
                    project_id,
                    cookie=cookie,
                )
                if session_status != 200 or not session_id:
                    return [
                        session_status,
                        {
                            "error": "update_video_failed",
                            "message": "未获取到项目 sessionId",
                            "data": session_data,
                        },
                    ]

            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_timeline.yaml",
                "update_video",
                cookie=cookie,
                project_id=project_id,
                session_id=session_id,
                video_list=video_list,
            )
        except Exception as e:
            logger.error(f"更新时间轴视频轨失败，错误: {e}")
            return [None, {"error": "update_video_failed", "message": str(e)}]

    def wait_for_video_visible_updated(self, project_id, visible, video_id=0, cookie=None, timeout=30, interval=2):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_project_source(project_id, cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if status_code == 200 and data.get("success") is True:
                video_detail = self.find_video_detail(data, video_id=video_id)
                if video_detail and video_detail.get("hideOrMute") == visible:
                    return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_video_visible_updated", "latest": latest_response}]
