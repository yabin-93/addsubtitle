import copy

import allure
import pytest

from api_moudle.project.home.proj_list import ProjList
from api_moudle.project.translate.translate_create import TranslateCreate
from api_moudle.project.translate.translate_sentence import TranslateSentence
from common.yaml_util import read_yaml, write_yaml


@allure.epic("Translate")
class TestTranslateSentence:
    EDITED_SENTENCE_TEXT = "\u81ea\u52a8\u5316\u6d4b\u8bd5\u53e5\u5b50"

    @staticmethod
    def _has_available_sentences(project_id):
        status_code, data = TranslateSentence().get_project_sentence_list(project_id)
        return (
            status_code == 200
            and isinstance(data, dict)
            and data.get("success") is True
            and isinstance(data.get("data", {}).get("transList"), list)
            and isinstance(data.get("data", {}).get("oriList"), list)
            and len(data.get("data", {}).get("oriList", [])) > 0
            and len(data.get("data", {}).get("transList", [])) > 0
        )

    @classmethod
    def _get_target_project_id(cls):
        status_code, proj_data = ProjList().get_proj_list(pageSize=50)
        assert status_code == 200, f"获取项目列表失败: {proj_data}"
        rows = proj_data.get("data", {}).get("rows", [])
        assert rows, f"项目列表为空: {proj_data}"

        for key in ("translate_sentence_project_id", "translate_test_project_id", "translate_created_project_id"):
            project_id = read_yaml(key, default=None)
            if project_id is None:
                continue
            if cls._has_available_sentences(project_id):
                write_yaml({"translate_sentence_project_id": project_id})
                return project_id

        for project in sorted(rows, key=lambda item: int(item["id"]), reverse=True):
            project_id = project["id"]
            if cls._has_available_sentences(project_id):
                write_yaml({"translate_sentence_project_id": project_id})
                return project_id

        api = TranslateCreate()
        try:
            video_path = api.get_default_video_path()
        except FileNotFoundError as exc:
            pytest.skip(str(exc))

        status_code, flow_data = api.create_project_flow(video_path=video_path)
        assert status_code == 200
        assert flow_data["create"]["success"] is True

        project_id = flow_data["projectId"]
        write_yaml({"translate_sentence_project_id": project_id})
        return project_id

    @staticmethod
    def _create_fresh_target_project_id():
        api = TranslateCreate()
        try:
            video_path = api.get_default_video_path()
        except FileNotFoundError as exc:
            pytest.skip(str(exc))

        status_code, flow_data = api.create_project_flow(video_path=video_path)
        assert status_code == 200, flow_data
        assert flow_data["create"]["success"] is True

        project_id = flow_data["projectId"]
        write_yaml({"translate_sentence_project_id": project_id})
        return project_id

    @classmethod
    def _get_target_translation_sentence(cls, sentence_data):
        trans_list = sentence_data.get("data", {}).get("transList", [])
        for sentence_item in trans_list:
            if (
                sentence_item.get("id") is not None
                and isinstance(sentence_item.get("text"), str)
                and sentence_item.get("text")
                and isinstance(sentence_item.get("speaker"), str)
                and sentence_item.get("speaker")
            ):
                return copy.deepcopy(sentence_item)
        raise AssertionError("No editable translation sentence was found")

    @classmethod
    def _build_edited_sentence_text(cls, original_text):
        if original_text != cls.EDITED_SENTENCE_TEXT:
            return cls.EDITED_SENTENCE_TEXT
        return cls.EDITED_SENTENCE_TEXT + "2"

    @allure.feature("Sentence List")
    @allure.story("Get Translation Project Sentence List")
    @allure.title("Get Translation Project Sentence List")
    @pytest.mark.P0
    def test_get_translation_project_sentence_list(self):
        project_id = self._get_target_project_id()

        status_code, data = TranslateSentence().wait_for_project_sentence_ready(
            project_id,
            timeout=120,
            interval=3,
        )

        assert status_code == 200
        assert data["success"] is True
        assert data["code"] == 0
        assert data["msg"] == "success"
        assert isinstance(data["data"]["oriList"], list)
        assert len(data["data"]["oriList"]) > 0

        first_sentence = data["data"]["oriList"][0]
        assert isinstance(first_sentence["id"], int)
        assert first_sentence["startTime"] >= 0
        assert first_sentence["duration"] > 0
        assert isinstance(first_sentence["text"], str)
        assert first_sentence["text"]
        assert first_sentence["audioUrl"].startswith("http")
        assert first_sentence["audioUrl"].endswith(".wav")
        assert isinstance(first_sentence["speaker"], str)
        assert first_sentence["speaker"]
        assert isinstance(first_sentence["sentenceType"], int)

    @allure.feature("Sentence Edit")
    @allure.story("Edit Translation Sentence And Trigger Single TTS")
    @allure.title("Edit Translation Sentence And Trigger Single TTS")
    @pytest.mark.P0
    def test_edit_translation_sentence_and_single_tts(self):
        sentence_api = TranslateSentence()
        project_id = self._create_fresh_target_project_id()

        ready_status, ready_data = sentence_api.wait_for_project_sentence_ready(
            project_id,
            timeout=120,
            interval=3,
        )
        assert ready_status == 200
        assert ready_data["success"] is True

        target_sentence = self._get_target_translation_sentence(ready_data)
        sentence_id = target_sentence["id"]
        detail_status, detail_data = sentence_api.wait_for_sentence_detail_ready(
            project_id,
            [sentence_id],
            timeout=30,
            interval=2,
        )
        assert detail_status == 200
        assert detail_data["success"] is True

        target_sentence = sentence_api.find_sentence_item(
            detail_data,
            sentence_id=sentence_id,
            sentence_type=1,
        )
        assert target_sentence is not None

        original_text = target_sentence["text"]
        edited_text = self._build_edited_sentence_text(original_text)

        session_status, session_id, session_data = sentence_api.get_project_session_id(project_id)
        assert session_status == 200, session_data
        assert session_id is not None

        edit_item = sentence_api.build_batch_edit_sentence_item(
            target_sentence,
            text=edited_text,
            is_edit=True,
        )
        edit_status, edit_data = sentence_api.batch_edit_sentence(
            project_id,
            sentence_list=[edit_item],
            session_id=session_id,
        )
        assert edit_status == 200, edit_data
        assert edit_data["success"] is True
        assert edit_data["code"] == 0

        updated_status, updated_data = sentence_api.wait_for_sentence_text_updated(
            project_id,
            sentence_id=sentence_id,
            expected_text=edited_text,
            sentence_type=1,
            timeout=30,
            interval=2,
        )
        assert updated_status == 200
        assert updated_data["success"] is True

        tts_status, tts_data = sentence_api.single_tts(
            project_id,
            sentence_id=sentence_id,
            text=edited_text,
            session_id=session_id,
        )
        assert tts_status == 200, tts_data
        assert tts_data["success"] is True
        assert tts_data["code"] == 0

        generating_status, generating_data = sentence_api.wait_for_sentence_tts_started(
            project_id,
            sentence_id=sentence_id,
            expected_text=edited_text,
            sentence_type=1,
            timeout=30,
            interval=2,
        )
        assert generating_status == 200
        assert generating_data["success"] is True
        assert generating_data["code"] == 0

        updated_sentence = sentence_api.find_sentence_item(
            generating_data,
            sentence_id=sentence_id,
            sentence_type=1,
        )
        assert updated_sentence is not None
        assert updated_sentence["text"] == edited_text
        assert updated_sentence["isGenerating"] is True
        assert updated_sentence["isEdit"] is True
        assert updated_sentence["duration"] > 0
        assert updated_sentence["materialDuration"] > 0
