import json as json_lib
import time

from api_moudle.project.add_subtitle.add_subtitle_create import ProjCreate
from api_moudle.project.home.base_api import BaseApi
from common.auth_util import get_cookie
from common.logger import logger
from common.yaml_util import read_yaml


class ProjExport(BaseApi):
    DEFAULT_EXPORT_VERSION = 1
    DEFAULT_EXPORT_RESOLUTION = 1
    DEFAULT_EXPORT_DEVICE_TYPE = "desktop"
    DEFAULT_EXPORT_HEADERS = "content-type: application/json;charset=utf-8"

    @staticmethod
    def normalize_export_progress(progress):
        return int(progress)

    @staticmethod
    def normalize_subtitle_arr_id(subtitle_arr_id):
        try:
            return int(subtitle_arr_id)
        except (TypeError, ValueError):
            return subtitle_arr_id

    @staticmethod
    def build_export_words(segments):
        export_words = []
        for index, segment in enumerate(segments or [], start=1):
            if not isinstance(segment, dict):
                continue

            text = segment.get("text")
            if text is None:
                continue

            segment_id = segment.get("id", index)
            try:
                segment_id = int(segment_id)
            except (TypeError, ValueError):
                pass

            word_offset = segment.get("wordOffset", segment.get("offset", 0)) or 0
            duration = segment.get("duration", 0) or 0
            export_words.append(
                {
                    "id": segment_id,
                    "text": text,
                    "wordOffset": int(word_offset),
                    "duration": int(duration),
                }
            )

        return export_words

    @classmethod
    def build_export_subtitle_json(cls, subtitle_data):
        payload = subtitle_data.get("data", {}) if isinstance(subtitle_data, dict) else {}
        ori_list = payload.get("oriList", [])
        trans_map = {
            cls.normalize_subtitle_arr_id(item.get("subtitleArrId")): item
            for item in payload.get("transList", [])
            if isinstance(item, dict) and item.get("subtitleArrId") is not None
        }

        export_items = []
        for ori_item in ori_list:
            if not isinstance(ori_item, dict):
                continue

            subtitle_arr_id = ori_item.get("subtitleArrId")
            if subtitle_arr_id is None:
                continue

            trans_item = trans_map.get(cls.normalize_subtitle_arr_id(subtitle_arr_id))
            words = cls.build_export_words(ori_item.get("segment", []))
            translate_words = cls.build_export_words(trans_item.get("segment", [])) if trans_item else []
            if not words or not translate_words:
                continue

            export_items.append(
                {
                    "startTime": int(ori_item.get("startTime", 0) or 0),
                    "duration": int(sum(word.get("duration", 0) or 0 for word in words)),
                    "subtitleArrId": cls.normalize_subtitle_arr_id(subtitle_arr_id),
                    "speed": ori_item.get("speed", 1) or 1,
                    "words": words,
                    "translateWords": translate_words,
                }
            )

        return export_items

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
                    "message": "project sessionId not found",
                    "data": detail_data,
                },
            ]

        return [200, session_id, detail_data]

    @staticmethod
    def _extract_token_from_cookie(cookie):
        if not cookie or "talecast_token=" not in cookie:
            return None
        return cookie.split("talecast_token=", 1)[1].split(";", 1)[0]

    def _resolve_frontend_auth(self, cookie=None, force_refresh=False):
        active_cookie = cookie or get_cookie(force_refresh=force_refresh)
        token = read_yaml("token", default=None) or self._extract_token_from_cookie(active_cookie)
        if token is None and cookie is None and not force_refresh:
            return self._resolve_frontend_auth(cookie=None, force_refresh=True)
        return active_cookie, f"Bearer {token}" if token else None

    def _run_export_request(
        self,
        api_name,
        project_id,
        subtitle_json,
        resolution=DEFAULT_EXPORT_RESOLUTION,
        lip_sync=False,
        device_type=DEFAULT_EXPORT_DEVICE_TYPE,
        export_headers=DEFAULT_EXPORT_HEADERS,
        cookie=None,
    ):
        if not subtitle_json:
            raise ValueError("subtitle_json cannot be empty")

        subtitle_json_payload = (
            subtitle_json
            if isinstance(subtitle_json, str)
            else json_lib.dumps(subtitle_json, ensure_ascii=False)
        )
        return self.run_authed_request(
            "project/add_subtitle/add_subtitle_export.yaml",
            api_name,
            cookie=cookie,
            project_id=project_id,
            subtitle_json=subtitle_json_payload,
            export_headers=export_headers,
            resolution=int(resolution),
            lip_sync=bool(lip_sync),
            device_type=device_type,
        )

    def _run_frontend_request(self, api_name, project_id, session_id, cookie=None):
        provided_cookie = cookie is not None
        active_cookie, authorization = self._resolve_frontend_auth(cookie=cookie, force_refresh=False)
        response = self.run_request(
            "project/add_subtitle/add_subtitle_export.yaml",
            api_name,
            project_id=project_id,
            session_id=session_id,
            cookie=active_cookie,
            authorization=authorization,
        )

        if not provided_cookie and response and response[0] == 401:
            active_cookie, authorization = self._resolve_frontend_auth(cookie=None, force_refresh=True)
            response = self.run_request(
                "project/add_subtitle/add_subtitle_export.yaml",
                api_name,
                project_id=project_id,
                session_id=session_id,
                cookie=active_cookie,
                authorization=authorization,
            )

        return response

    def export_backend(
        self,
        project_id,
        subtitle_json,
        resolution=DEFAULT_EXPORT_RESOLUTION,
        lip_sync=False,
        device_type=DEFAULT_EXPORT_DEVICE_TYPE,
        export_headers=DEFAULT_EXPORT_HEADERS,
        cookie=None,
    ):
        try:
            return self._run_export_request(
                "export_backend",
                project_id=project_id,
                subtitle_json=subtitle_json,
                resolution=resolution,
                lip_sync=lip_sync,
                device_type=device_type,
                export_headers=export_headers,
                cookie=cookie,
            )
        except Exception as e:
            logger.error(f"export_backend failed: {e}")
            return [None, {"error": "export_backend_failed", "message": str(e)}]

    def project_point(self, project_id, session_id, cookie=None):
        try:
            return self._run_frontend_request(
                "project_point",
                project_id=project_id,
                session_id=session_id,
                cookie=cookie,
            )
        except Exception as e:
            logger.error(f"project_point failed: {e}")
            return [None, {"error": "project_point_failed", "message": str(e)}]

    def export_front(self, project_id, session_id, cookie=None):
        try:
            return self._run_frontend_request(
                "export_front",
                project_id=project_id,
                session_id=session_id,
                cookie=cookie,
            )
        except Exception as e:
            logger.error(f"export_front failed: {e}")
            return [None, {"error": "export_front_failed", "message": str(e)}]

    def export_frontend(self, project_id, session_id=None, cookie=None, send_export_click=True):
        if session_id is None:
            session_status, session_id, session_data = self.get_project_session_id(project_id, cookie=cookie)
            if session_status != 200 or not session_id:
                return [
                    session_status,
                    {
                        "error": "export_frontend_failed",
                        "message": "project sessionId not found",
                        "data": session_data,
                    },
                ]

        point_status, point_data = self.project_point(project_id, session_id=session_id, cookie=cookie)
        result = {
            "sessionId": session_id,
            "projectPoint": {"status_code": point_status, "data": point_data},
        }
        if point_status != 200 or (isinstance(point_data, dict) and point_data.get("success") is False):
            return [point_status, result]

        event_status = None
        event_data = None
        if send_export_click:
            event_status, event_data = ProjCreate().conform_event(
                "export_click",
                project_id=project_id,
                cookie=cookie,
            )
            result["eventConform"] = {"status_code": event_status, "data": event_data}

        export_status, export_data = self.export_front(project_id, session_id=session_id, cookie=cookie)
        result["exportFront"] = {"status_code": export_status, "data": export_data}
        return [export_status, result]

    def get_export_progress(self, project_id, session_id, version=DEFAULT_EXPORT_VERSION, cookie=None):
        if not session_id:
            raise ValueError("session_id is required")

        try:
            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_export.yaml",
                "get_export_progress",
                cookie=cookie,
                project_id=project_id,
                version=int(version),
                session_id=session_id,
            )
        except Exception as e:
            logger.error(f"get_export_progress failed: {e}")
            return [None, {"error": "get_export_progress_failed", "message": str(e)}]

    def wait_for_export_completed(
        self,
        project_id,
        session_id,
        version=DEFAULT_EXPORT_VERSION,
        cookie=None,
        timeout=900,
        interval=10,
    ):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_export_progress(
                project_id,
                session_id=session_id,
                version=version,
                cookie=cookie,
            )
            latest_response = {"status_code": status_code, "data": data}

            if status_code == 200 and isinstance(data, dict) and data.get("success") is True:
                try:
                    if self.normalize_export_progress(data.get("data")) == 100:
                        return [200, data]
                except (TypeError, ValueError):
                    pass

            time.sleep(interval)

        return [408, {"stage": "wait_for_export_completed", "latest": latest_response}]
