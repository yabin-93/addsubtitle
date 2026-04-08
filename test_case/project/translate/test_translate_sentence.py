import allure
import pytest

from api_moudle.project.home.proj_list import ProjList
from api_moudle.project.translate.translate_create import TranslateCreate
from api_moudle.project.translate.translate_sentence import TranslateSentence
from common.yaml_util import read_yaml, write_yaml


@allure.epic("Translate")
class TestTranslateSentence:
    @staticmethod
    def _has_available_sentences(project_id):
        status_code, data = TranslateSentence().get_project_sentence_list(project_id)
        return (
            status_code == 200
            and isinstance(data, dict)
            and data.get("success") is True
            and isinstance(data.get("data", {}).get("oriList"), list)
            and len(data.get("data", {}).get("oriList", [])) > 0
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
