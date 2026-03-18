import time

from api_moudle.project.home.base_api import BaseApi
from api_moudle.project.add_subtitle.add_subtitle_create import ProjCreate
from common.logger import logger
from common.yaml_util import read_yaml, write_yaml


class ProjSubtitle(BaseApi):
    VALID_SUBTITLE_SHOW_ENUMS = {0, 1, 2, 3}
    VALID_SUBTITLE_TYPES = {0, 1}
    LIST_KEY_BY_TYPE = {0: "oriList", 1: "transList"}
    SEGMENT_KEY_BY_TYPE = {0: "oriSegments", 1: "transSegments"}
    DEFAULT_NEW_SUBTITLE_DURATION = 900

    @classmethod
    def normalize_subtitle_show_enum(cls, subtitle_show_enum):
        if subtitle_show_enum not in cls.VALID_SUBTITLE_SHOW_ENUMS:
            raise ValueError(
                f"subtitle_show_enum 只能是 {sorted(cls.VALID_SUBTITLE_SHOW_ENUMS)} 中的一个"
            )
        return subtitle_show_enum

    @classmethod
    def normalize_subtitle_type(cls, subtitle_type):
        if subtitle_type not in cls.VALID_SUBTITLE_TYPES:
            raise ValueError(f"subtitle_type 只能是 {sorted(cls.VALID_SUBTITLE_TYPES)} 中的一个")
        return subtitle_type

    @staticmethod
    def normalize_char_num(char_num):
        api_char_num = int(char_num)
        if api_char_num <= 0:
            raise ValueError("char_num must be greater than 0")
        return api_char_num

    @classmethod
    def get_list_key(cls, subtitle_type):
        return cls.LIST_KEY_BY_TYPE[cls.normalize_subtitle_type(subtitle_type)]

    @classmethod
    def get_segment_key(cls, subtitle_type):
        return cls.SEGMENT_KEY_BY_TYPE[cls.normalize_subtitle_type(subtitle_type)]

    @staticmethod
    def extract_segment_texts(subtitle_item):
        return [segment.get("text") for segment in subtitle_item.get("segment", [])]

    @staticmethod
    def join_segment_texts(subtitle_item):
        return " ".join(text for text in ProjSubtitle.extract_segment_texts(subtitle_item) if text)

    @staticmethod
    def generate_client_id(offset=0):
        return int(time.time() * 1000) + offset

    @staticmethod
    def estimate_subtitle_end_time(subtitle_item):
        start_time = subtitle_item.get("startTime") or 0
        total_duration = sum((segment.get("duration") or 0) for segment in subtitle_item.get("segment", []))
        return start_time + total_duration

    @classmethod
    def plan_new_subtitle_slot(cls, subtitle_items, min_gap=500, default_duration=None):
        if not subtitle_items:
            raise ValueError("subtitle_items cannot be empty")

        default_duration = default_duration or cls.DEFAULT_NEW_SUBTITLE_DURATION
        for previous_item, next_item in zip(subtitle_items, subtitle_items[1:]):
            start_time = cls.estimate_subtitle_end_time(previous_item)
            next_start_time = next_item.get("startTime") or start_time
            gap = next_start_time - start_time
            if gap >= min_gap:
                return {
                    "previous_item": previous_item,
                    "next_item": next_item,
                    "start_time": start_time,
                    "duration": gap,
                }

        previous_item = subtitle_items[-1]
        return {
            "previous_item": previous_item,
            "next_item": None,
            "start_time": cls.estimate_subtitle_end_time(previous_item),
            "duration": default_duration,
        }

    @classmethod
    def build_add_subtitle_payload(
        cls,
        previous_subtitle_item,
        subtitle_arr_id=None,
        start_time=None,
        duration=None,
        text="",
        segment_id=None,
    ):
        subtitle_arr_id = subtitle_arr_id or cls.generate_client_id()
        start_time = cls.estimate_subtitle_end_time(previous_subtitle_item) if start_time is None else start_time
        duration = cls.DEFAULT_NEW_SUBTITLE_DURATION if duration is None else duration
        segment_id = segment_id or cls.generate_client_id(offset=1)

        segment = {
            "id": segment_id,
            "text": text,
            "duration": max(1, int(duration)),
            "wordOffset": 0,
        }
        return {
            "subtitle_arr_id": subtitle_arr_id,
            "start_time": int(start_time),
            "speech_id": previous_subtitle_item.get("speechId"),
            "pre_subtitle_arr_id": previous_subtitle_item.get("subtitleArrId"),
            "ori_segments": [dict(segment)],
            "trans_segments": [dict(segment)],
        }

    @classmethod
    def find_subtitle_item(
        cls,
        subtitle_data,
        subtitle_id=None,
        subtitle_arr_id=None,
        subtitle_type=1,
    ):
        data = subtitle_data.get("data", {}) if isinstance(subtitle_data, dict) else {}
        subtitle_list = data.get(cls.get_list_key(subtitle_type), [])

        for item in subtitle_list:
            if subtitle_id is not None and item.get("id") == subtitle_id:
                return item
            if subtitle_arr_id is not None and item.get("subtitleArrId") == subtitle_arr_id:
                return item
        return None

    @classmethod
    def build_segments(cls, subtitle_item, edited_texts=None):
        segments = subtitle_item.get("segment", [])
        original_texts = cls.extract_segment_texts(subtitle_item)
        edited_texts = edited_texts or original_texts

        if len(segments) != len(edited_texts):
            raise ValueError("edited_texts 的长度必须与字幕分段数量一致")

        built_segments = []
        for segment, edited_text in zip(segments, edited_texts):
            built_segments.append(
                {
                    "id": segment.get("id"),
                    "offset": segment.get("wordOffset", segment.get("offset", 0)),
                    "duration": segment.get("duration"),
                    "text": edited_text,
                }
            )
        return built_segments

    @classmethod
    def build_batch_edit_item(cls, subtitle_item, edited_texts=None, subtitle_type=None):
        api_subtitle_type = cls.normalize_subtitle_type(
            subtitle_item.get("subtitleType") if subtitle_type is None else subtitle_type
        )
        original_texts = cls.extract_segment_texts(subtitle_item)
        has_text_changed = edited_texts is not None and list(edited_texts) != original_texts
        segment_key = cls.get_segment_key(api_subtitle_type)

        item = {
            "id": subtitle_item.get("id"),
            "projectId": subtitle_item.get("projectId"),
            "subtitleType": api_subtitle_type,
            "number": subtitle_item.get("number"),
            "speechId": subtitle_item.get("speechId"),
            "subtitleArrId": subtitle_item.get("subtitleArrId"),
            "startTime": subtitle_item.get("startTime"),
            "isEdit": has_text_changed or subtitle_item.get("isEdit", False),
            "isTranslating": subtitle_item.get("isTranslating", False),
            "gmtCreated": subtitle_item.get("gmtCreated"),
            "gmtModified": subtitle_item.get("gmtModified"),
        }
        item[segment_key] = cls.build_segments(subtitle_item, edited_texts=edited_texts)
        return item

    def get_project_subtitle(self, project_id, cookie=None):
        try:
            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_subtitle.yaml",
                "get_project_subtitle",
                cookie=cookie,
                project_id=project_id,
            )
        except Exception as e:
            logger.error(f"获取项目字幕失败，错误: {e}")
            return [None, {"error": "get_project_subtitle_failed", "message": str(e)}]

    def get_subtitle_by_arr_ids(self, project_id, arr_ids, cookie=None):
        try:
            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_subtitle.yaml",
                "get_subtitle_by_arr_ids",
                cookie=cookie,
                project_id=project_id,
                arr_ids=arr_ids,
            )
        except Exception as e:
            logger.error(f"按字幕分组 ID 获取字幕失败，错误: {e}")
            return [None, {"error": "get_subtitle_by_arr_ids_failed", "message": str(e)}]

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
    # 批量编辑字幕
    def batch_edit_subtitle(self, project_id, subtitle_list, session_id=None, cookie=None):
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
                            "error": "batch_edit_subtitle_failed",
                            "message": "未获取到项目 sessionId",
                            "data": session_data,
                        },
                    ]

            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_subtitle.yaml",
                "batch_edit_subtitle",
                cookie=cookie,
                project_id=project_id,
                session_id=session_id,
                subtitle_list=subtitle_list,
            )
        except Exception as e:
            logger.error(f"批量编辑字幕失败，错误: {e}")
            return [None, {"error": "batch_edit_subtitle_failed", "message": str(e)}]

    def add_new_subtitle(
        self,
        project_id,
        subtitle_arr_id,
        start_time,
        speech_id,
        pre_subtitle_arr_id,
        ori_segments,
        trans_segments,
        session_id=None,
        cookie=None,
    ):
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
                            "error": "add_new_subtitle_failed",
                            "message": "未获取到项目 sessionId",
                            "data": session_data,
                        },
                    ]

            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_subtitle.yaml",
                "add_new_subtitle",
                cookie=cookie,
                project_id=project_id,
                session_id=session_id,
                subtitle_arr_id=subtitle_arr_id,
                start_time=start_time,
                speech_id=speech_id,
                pre_subtitle_arr_id=pre_subtitle_arr_id,
                ori_segments=ori_segments,
                trans_segments=trans_segments,
            )
        except Exception as e:
            logger.error(f"新增字幕失败，错误: {e}")
            return [None, {"error": "add_new_subtitle_failed", "message": str(e)}]
    # 字幕批量翻译
    def subtitle_batch_translate(self, project_id, arr_ids, session_id=None, cookie=None):
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
                            "error": "subtitle_batch_translate_failed",
                            "message": "未获取到项目 sessionId",
                            "data": session_data,
                        },
                    ]

            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_subtitle.yaml",
                "subtitle_batch_translate",
                cookie=cookie,
                project_id=project_id,
                session_id=session_id,
                arr_ids=arr_ids,
            )
        except Exception as e:
            logger.error(f"触发字幕翻译失败，错误: {e}")
            return [None, {"error": "subtitle_batch_translate_failed", "message": str(e)}]
    # 删除字幕框
    def delete_subtitle(self, project_id, subtitle_arr_id, session_id=None, cookie=None):
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
                            "error": "delete_subtitle_failed",
                            "message": "未获取到项目 sessionId",
                            "data": session_data,
                        },
                    ]

            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_subtitle.yaml",
                "delete_subtitle",
                cookie=cookie,
                project_id=project_id,
                session_id=session_id,
                subtitle_arr_id=subtitle_arr_id,
            )
        except Exception as e:
            logger.error(f"删除字幕失败，错误: {e}")
            return [None, {"error": "delete_subtitle_failed", "message": str(e)}]

    def update_subtitle_show(self, project_id, subtitle_show_enum, cookie=None):
        api_subtitle_show_enum = self.normalize_subtitle_show_enum(subtitle_show_enum)
        try:
            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_subtitle.yaml",
                "update_subtitle_show",
                cookie=cookie,
                project_id=project_id,
                subtitle_show_enum=api_subtitle_show_enum,
            )
        except Exception as e:
            logger.error(f"切换字幕显示状态失败，错误: {e}")
            return [None, {"error": "update_subtitle_show_failed", "message": str(e)}]

    def wait_for_subtitle_show_updated(self, project_id, subtitle_show_enum, cookie=None, timeout=30, interval=2):
        expected_subtitle_show = self.normalize_subtitle_show_enum(subtitle_show_enum)
        deadline = time.time() + timeout
        latest_response = None
        project_create_api = ProjCreate()

        while time.time() < deadline:
            # 字幕显示状态体现在项目详情里，这里轮询详情确认切换是否生效。
            status_code, data = project_create_api.get_project_detail(project_id, cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if (
                status_code == 200
                and data.get("success") is True
                and data.get("data", {}).get("subtitleShow") == expected_subtitle_show
            ):
                return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_subtitle_show_updated", "latest": latest_response}]

    def update_char_num(self, project_id, char_num, cookie=None):
        api_char_num = self.normalize_char_num(char_num)
        try:
            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_subtitle.yaml",
                "update_char_num",
                cookie=cookie,
                project_id=project_id,
                char_num=api_char_num,
            )
        except Exception as e:
            logger.error(f"update_char_num failed: {e}")
            return [None, {"error": "update_char_num_failed", "message": str(e)}]

    def wait_for_char_num_updated(self, project_id, char_num, cookie=None, timeout=30, interval=2):
        expected_char_num = self.normalize_char_num(char_num)
        deadline = time.time() + timeout
        latest_response = None
        project_create_api = ProjCreate()

        while time.time() < deadline:
            status_code, data = project_create_api.get_project_detail(project_id, cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            current_char_num = data.get("data", {}).get("charNum") if isinstance(data, dict) else None
            if status_code == 200 and data.get("success") is True and current_char_num is not None:
                if self.normalize_char_num(current_char_num) == expected_char_num:
                    return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_char_num_updated", "latest": latest_response}]

    def wait_for_subtitle_text_updated(
        self,
        project_id,
        subtitle_id,
        expected_texts,
        subtitle_type=1,
        cookie=None,
        timeout=30,
        interval=2,
    ):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_project_subtitle(project_id, cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if status_code == 200 and data.get("success") is True:
                subtitle_item = self.find_subtitle_item(
                    data,
                    subtitle_id=subtitle_id,
                    subtitle_type=subtitle_type,
                )
                if subtitle_item and self.extract_segment_texts(subtitle_item) == expected_texts:
                    return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_subtitle_text_updated", "latest": latest_response}]

    def wait_for_subtitle_created(
        self,
        project_id,
        subtitle_arr_id,
        cookie=None,
        timeout=30,
        interval=2,
    ):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_subtitle_by_arr_ids(
                project_id,
                arr_ids=[subtitle_arr_id],
                cookie=cookie,
            )
            latest_response = {"status_code": status_code, "data": data}

            if status_code == 200 and data.get("success") is True:
                ori_item = self.find_subtitle_item(
                    data,
                    subtitle_arr_id=subtitle_arr_id,
                    subtitle_type=0,
                )
                trans_item = self.find_subtitle_item(
                    data,
                    subtitle_arr_id=subtitle_arr_id,
                    subtitle_type=1,
                )
                if ori_item is not None and trans_item is not None:
                    return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_subtitle_created", "latest": latest_response}]

    def wait_for_subtitle_deleted(
        self,
        project_id,
        subtitle_arr_id,
        cookie=None,
        timeout=30,
        interval=2,
    ):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_project_subtitle(project_id, cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if status_code == 200 and data.get("success") is True:
                ori_item = self.find_subtitle_item(
                    data,
                    subtitle_arr_id=subtitle_arr_id,
                    subtitle_type=0,
                )
                trans_item = self.find_subtitle_item(
                    data,
                    subtitle_arr_id=subtitle_arr_id,
                    subtitle_type=1,
                )
                if ori_item is None and trans_item is None:
                    return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_subtitle_deleted", "latest": latest_response}]

    def wait_for_translation_result(
        self,
        project_id,
        subtitle_arr_id,
        expected_original_texts=None,
        previous_translation_texts=None,
        cookie=None,
        timeout=120,
        interval=3,
    ):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_subtitle_by_arr_ids(
                project_id,
                arr_ids=[subtitle_arr_id],
                cookie=cookie,
            )
            latest_response = {"status_code": status_code, "data": data}

            if status_code == 200 and data.get("success") is True:
                ori_item = self.find_subtitle_item(
                    data,
                    subtitle_arr_id=subtitle_arr_id,
                    subtitle_type=0,
                )
                trans_item = self.find_subtitle_item(
                    data,
                    subtitle_arr_id=subtitle_arr_id,
                    subtitle_type=1,
                )
                if not ori_item or not trans_item:
                    time.sleep(interval)
                    continue

                ori_texts = self.extract_segment_texts(ori_item)
                trans_texts = self.extract_segment_texts(trans_item)
                if expected_original_texts is not None and ori_texts != expected_original_texts:
                    time.sleep(interval)
                    continue
                if trans_item.get("isTranslating"):
                    time.sleep(interval)
                    continue
                if not any(trans_texts):
                    time.sleep(interval)
                    continue
                if previous_translation_texts is not None and trans_texts == previous_translation_texts:
                    time.sleep(interval)
                    continue
                return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_translation_result", "latest": latest_response}]

    def wait_for_project_subtitle_ready(self, project_id, cookie=None, timeout=90, interval=3):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            # 语音识别和翻译是异步生成的，这里等原文和译文列表都准备好。
            status_code, data = self.get_project_subtitle(project_id, cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if status_code == 200 and data.get("success") is True:
                payload = data.get("data", {})
                ori_list = payload.get("oriList")
                trans_list = payload.get("transList")
                if isinstance(ori_list, list) and isinstance(trans_list, list) and ori_list and trans_list:
                    write_yaml({"subtitle_project_id": project_id})
                    return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_project_subtitle_ready", "latest": latest_response}]


if __name__ == "__main__":
    project_id = read_yaml(
        "uploaded_video_project_id",
        default=read_yaml("created_project_id", default=None),
    )
    if project_id is None:
        print("未找到项目 ID")
    else:
        print(ProjSubtitle().get_project_subtitle(project_id))
