import time

from api_moudle.project.home.base_api import BaseApi
from api_moudle.project.translate.translate_create import TranslateCreate
from common.logger import logger


class TranslateSentence(BaseApi):
    YAML_PATH = "project/translate/translate_sentence.yaml"
    LIST_KEY_BY_TYPE = {0: "oriList", 1: "transList"}

    @classmethod
    def normalize_sentence_type(cls, sentence_type):
        if sentence_type not in cls.LIST_KEY_BY_TYPE:
            raise ValueError(f"sentence_type must be one of {sorted(cls.LIST_KEY_BY_TYPE)}")
        return sentence_type

    @classmethod
    def get_list_key(cls, sentence_type):
        return cls.LIST_KEY_BY_TYPE[cls.normalize_sentence_type(sentence_type)]

    @classmethod
    def find_sentence_item(cls, sentence_data, sentence_id=None, sentence_type=1):
        payload = sentence_data.get("data", {}) if isinstance(sentence_data, dict) else {}
        sentence_list = payload.get(cls.get_list_key(sentence_type), [])

        for item in sentence_list:
            if sentence_id is None or item.get("id") == sentence_id:
                return item
        return None

    @classmethod
    def build_batch_edit_sentence_item(
        cls,
        sentence_item,
        text=None,
        audio_url=None,
        duration=None,
        material_duration=None,
        volume=None,
        speed=None,
        is_edit=None,
        is_generating=None,
        track_index=None,
        mute=None,
        speaker=None,
        speaker_id=None,
        translating=None,
        is_edit_finish=None,
    ):
        if not isinstance(sentence_item, dict):
            raise ValueError("sentence_item must be a dict")

        item = {
            "id": sentence_item.get("id"),
            "startTime": sentence_item.get("startTime"),
            "offset": sentence_item.get("offset", 0),
            "trackOffset": sentence_item.get("trackOffset", 0),
            "duration": sentence_item.get("duration"),
            "materialDuration": sentence_item.get("materialDuration", sentence_item.get("duration")),
            "volume": sentence_item.get("volume", 1),
            "speed": sentence_item.get("speed", 1),
            "text": sentence_item.get("text", ""),
            "audioUrl": sentence_item.get("audioUrl", ""),
            "isEdit": sentence_item.get("isEdit", False),
            "isGenerating": sentence_item.get("isGenerating", False),
            "trackIndex": sentence_item.get("trackIndex", 0),
            "mute": sentence_item.get("mute", False),
            "speaker": sentence_item.get("speaker"),
            "speakerId": sentence_item.get("speakerId"),
            "translating": sentence_item.get("translating", False),
            "sentenceType": sentence_item.get("sentenceType"),
        }

        overrides = {
            "text": text,
            "audioUrl": audio_url,
            "duration": duration,
            "materialDuration": material_duration,
            "volume": volume,
            "speed": speed,
            "isEdit": is_edit,
            "isGenerating": is_generating,
            "trackIndex": track_index,
            "mute": mute,
            "speaker": speaker,
            "speakerId": speaker_id,
            "translating": translating,
        }
        for key, value in overrides.items():
            if value is not None:
                item[key] = value

        if is_edit_finish is not None:
            item["isEditFinish"] = is_edit_finish

        return item

    def get_project_session_id(self, project_id, cookie=None):
        detail_status, detail_data = TranslateCreate().get_project_detail(project_id, cookie=cookie)
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

    def get_project_sentence_list(self, project_id, cookie=None):
        return self.run_authed_request(
            self.YAML_PATH,
            "get_project_sentence_list",
            cookie=cookie,
            project_id=project_id,
        )

    def get_project_sentence_detail(self, project_id, sentence_ids, cookie=None):
        return self.run_authed_request(
            self.YAML_PATH,
            "get_project_sentence_detail",
            cookie=cookie,
            project_id=project_id,
            sentence_ids=sentence_ids,
        )

    def _run_with_session_retry(self, api_name, project_id, payload, session_id=None, cookie=None):
        active_session_id = session_id
        if active_session_id is None:
            session_status, active_session_id, session_data = self.get_project_session_id(project_id, cookie=cookie)
            if session_status != 200 or not active_session_id:
                return [
                    session_status,
                    {
                        "error": f"{api_name}_failed",
                        "message": "project sessionId not found",
                        "data": session_data,
                    },
                ]

        response = self.run_authed_request(
            self.YAML_PATH,
            api_name,
            cookie=cookie,
            project_id=project_id,
            session_id=active_session_id,
            **payload,
        )

        response_status, response_data = response
        if isinstance(response_data, dict) and response_data.get("code") == -33:
            session_status, fresh_session_id, session_data = self.get_project_session_id(project_id, cookie=cookie)
            if session_status != 200 or not fresh_session_id:
                return [
                    session_status,
                    {
                        "error": f"{api_name}_failed",
                        "message": "project sessionId refresh failed",
                        "data": session_data,
                    },
                ]
            if fresh_session_id != active_session_id:
                response = self.run_authed_request(
                    self.YAML_PATH,
                    api_name,
                    cookie=cookie,
                    project_id=project_id,
                    session_id=fresh_session_id,
                    **payload,
                )

        return response

    def batch_edit_sentence(self, project_id, sentence_list, session_id=None, cookie=None):
        if not sentence_list:
            raise ValueError("sentence_list cannot be empty")
        try:
            return self._run_with_session_retry(
                "batch_edit_sentence",
                project_id=project_id,
                payload={"sentence_list": sentence_list},
                session_id=session_id,
                cookie=cookie,
            )
        except Exception as exc:
            logger.error(f"batch_edit_sentence failed: {exc}")
            return [None, {"error": "batch_edit_sentence_failed", "message": str(exc)}]

    def single_tts(self, project_id, sentence_id, text, session_id=None, cookie=None):
        try:
            return self._run_with_session_retry(
                "single_tts",
                project_id=project_id,
                payload={"sentence_id": sentence_id, "text": text},
                session_id=session_id,
                cookie=cookie,
            )
        except Exception as exc:
            logger.error(f"single_tts failed: {exc}")
            return [None, {"error": "single_tts_failed", "message": str(exc)}]

    def wait_for_project_sentence_ready(self, project_id, cookie=None, timeout=120, interval=3):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_project_sentence_list(project_id, cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if (
                status_code == 200
                and isinstance(data, dict)
                and data.get("success") is True
                and isinstance(data.get("data", {}).get("oriList"), list)
                and isinstance(data.get("data", {}).get("transList"), list)
                and len(data.get("data", {}).get("oriList", [])) > 0
                and len(data.get("data", {}).get("transList", [])) > 0
            ):
                return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_project_sentence_ready", "latest": latest_response}]

    def wait_for_sentence_detail_ready(self, project_id, sentence_ids, cookie=None, timeout=120, interval=3):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_project_sentence_detail(project_id, sentence_ids, cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if (
                status_code == 200
                and isinstance(data, dict)
                and data.get("success") is True
                and isinstance(data.get("data", {}).get("oriList"), list)
                and isinstance(data.get("data", {}).get("transList"), list)
                and len(data.get("data", {}).get("oriList", [])) > 0
                and len(data.get("data", {}).get("transList", [])) > 0
            ):
                return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_sentence_detail_ready", "latest": latest_response}]

    def wait_for_sentence_text_updated(
        self,
        project_id,
        sentence_id,
        expected_text,
        sentence_type=1,
        cookie=None,
        timeout=30,
        interval=2,
    ):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_project_sentence_list(project_id, cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if status_code == 200 and isinstance(data, dict) and data.get("success") is True:
                sentence_item = self.find_sentence_item(data, sentence_id=sentence_id, sentence_type=sentence_type)
                if sentence_item and sentence_item.get("text") == expected_text:
                    return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_sentence_text_updated", "latest": latest_response}]

    def wait_for_sentence_tts_ready(
        self,
        project_id,
        sentence_id,
        expected_text=None,
        sentence_type=1,
        previous_audio_url=None,
        cookie=None,
        timeout=180,
        interval=3,
    ):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_project_sentence_detail(project_id, [sentence_id], cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if status_code == 200 and isinstance(data, dict) and data.get("success") is True:
                sentence_item = self.find_sentence_item(data, sentence_id=sentence_id, sentence_type=sentence_type)
                if not sentence_item:
                    time.sleep(interval)
                    continue
                if expected_text is not None and sentence_item.get("text") != expected_text:
                    time.sleep(interval)
                    continue
                if sentence_item.get("isGenerating") is True:
                    time.sleep(interval)
                    continue
                audio_url = sentence_item.get("audioUrl")
                if not audio_url:
                    time.sleep(interval)
                    continue
                if previous_audio_url is not None and audio_url == previous_audio_url:
                    time.sleep(interval)
                    continue
                if (sentence_item.get("duration") or 0) <= 0:
                    time.sleep(interval)
                    continue
                if (sentence_item.get("materialDuration") or 0) <= 0:
                    time.sleep(interval)
                    continue
                return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_sentence_tts_ready", "latest": latest_response}]

    def wait_for_sentence_tts_started(
        self,
        project_id,
        sentence_id,
        expected_text=None,
        sentence_type=1,
        cookie=None,
        timeout=60,
        interval=2,
    ):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_project_sentence_detail(project_id, [sentence_id], cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if status_code == 200 and isinstance(data, dict) and data.get("success") is True:
                sentence_item = self.find_sentence_item(data, sentence_id=sentence_id, sentence_type=sentence_type)
                if not sentence_item:
                    time.sleep(interval)
                    continue
                if expected_text is not None and sentence_item.get("text") != expected_text:
                    time.sleep(interval)
                    continue
                if sentence_item.get("isGenerating") is True:
                    return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_sentence_tts_started", "latest": latest_response}]
