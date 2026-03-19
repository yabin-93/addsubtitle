import copy

import allure
import pytest

from api_moudle.project.add_subtitle.add_subtitle_create import ProjCreate
from api_moudle.project.home.proj_list import ProjList
from api_moudle.project.add_subtitle.add_subtitle_subtitle import ProjSubtitle
from common.font_style_db import load_font_style_cases
from common.yaml_util import read_yaml, write_yaml


FONT_STYLE_CASES = [
    {
        "subtitleName": "\u963f\u91cc\u5df4\u5df4\u666e\u60e0\u4f53",
        "fontFamilyUrl": "https://web.talecast.ai/resource/resources/assets/captions/font_family_url/Alibaba-PuHuiTi-Regular.ttf",
    },
    {
        "subtitleName": "\u963f\u91cc\u5988\u5988\u6570\u9ed1\u4f53",
        "fontFamilyUrl": "https://web.talecast.ai/resource/resources/assets/captions/font_family_url/AlimamaShuHeiTi-Bold.otf",
    },
    {
        "subtitleName": "\u963f\u91cc\u5988\u5988\u5200\u96b6\u4f53",
        "fontFamilyUrl": "https://web.talecast.ai/resource/resources/assets/captions/font_family_url/Alimama-DaoLiTi.ttf",
    },
]
STYLE_VERIFY_KEYS = ("subtitleName", "fontFamilyUrl")


@allure.epic("AddSubtitle")
class TestProjSubtitle:
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
        assert status_code == 200, f"获取项目列表失败: {proj_data}"
        rows = proj_data["data"]["rows"]
        assert rows

        for key in ("uploaded_video_project_id", "subtitle_project_id", "created_project_id", "test_project_id"):
            project_id = read_yaml(key, default=None)
            if project_id is None:
                continue
            for project in rows:
                if project["id"] == project_id and TestProjSubtitle._has_available_subtitles(project_id):
                    return project_id

        for project in sorted(rows, key=lambda item: int(item["id"]), reverse=True):
            project_id = project["id"]
            if TestProjSubtitle._has_available_subtitles(project_id):
                write_yaml({"subtitle_project_id": project_id})
                return project_id

        latest_project = max(rows, key=lambda project: int(project["id"]))
        return latest_project["id"]

    @staticmethod
    def _get_first_subtitle_pair(subtitle_data):
        ori_list = subtitle_data["data"]["oriList"]
        trans_map = {item["subtitleArrId"]: item for item in subtitle_data["data"]["transList"]}
        for ori_item in ori_list:
            trans_item = trans_map.get(ori_item["subtitleArrId"])
            if trans_item is not None:
                return copy.deepcopy(ori_item), copy.deepcopy(trans_item)
        raise AssertionError("No available original/translated subtitle pair was found")

    @staticmethod
    def _get_ready_translation_item(subtitle_data):
        try:
            _, trans_item = TestProjSubtitle._get_first_subtitle_pair(subtitle_data)
        except AssertionError:
            return None

        translated_texts = ProjSubtitle.extract_segment_texts(trans_item)
        if trans_item.get("subtitleArrId") is None:
            return None
        if trans_item.get("isTranslating") is True:
            return None
        if not any(translated_texts):
            return None
        return trans_item

    @staticmethod
    def _build_original_edit_texts(original_texts):
        edited_texts = list(original_texts)
        if edited_texts:
            edited_texts[0] = "Please"
        if len(edited_texts) > 1:
            edited_texts[1] = "confirm"
        if len(edited_texts) > 2:
            edited_texts[2] = "carefully"
        return edited_texts

    @allure.feature("加字幕")
    @allure.story("项目字幕接口")
    @allure.title("获取项目字幕-正常场景")
    @pytest.mark.P0
    def test_get_project_subtitle(self):
        project_id = self._get_target_project_id()

        status_code, data = ProjSubtitle().wait_for_project_subtitle_ready(
            project_id,
            timeout=90,
            interval=3,
        )

        assert status_code == 200
        assert data["success"] is True
        assert data["msg"] == "success"
        assert isinstance(data["data"]["oriList"], list)
        assert isinstance(data["data"]["transList"], list)
        assert len(data["data"]["oriList"]) > 0
        assert len(data["data"]["transList"]) > 0

        first_ori = data["data"]["oriList"][0]
        first_trans = data["data"]["transList"][0]
        assert first_ori["projectId"] == project_id
        assert first_trans["projectId"] == project_id
        assert isinstance(first_ori["segment"], list)
        assert isinstance(first_trans["segment"], list)
        assert len(first_ori["segment"]) > 0
        assert len(first_trans["segment"]) > 0

    @allure.feature("加字幕")
    @allure.story("字幕内容更新")
    @allure.title("批量替换译文字幕")
    @pytest.mark.P0
    def test_batch_edit_subtitle(self):
        project_id = self._get_target_project_id()
        subtitle_api = ProjSubtitle()

        subtitle_status, subtitle_data = subtitle_api.wait_for_project_subtitle_ready(
            project_id,
            timeout=90,
            interval=3,
        )
        assert subtitle_status == 200
        assert subtitle_data["success"] is True

        target_subtitle = copy.deepcopy(subtitle_data["data"]["transList"][0])
        subtitle_id = target_subtitle["id"]
        original_texts = subtitle_api.extract_segment_texts(target_subtitle)
        assert original_texts

        expected_texts = list(original_texts)
        expected_texts[0] = "测试"
        if len(expected_texts) > 1:
            expected_texts[1] = "字幕"

        edit_item = subtitle_api.build_batch_edit_item(target_subtitle, edited_texts=expected_texts)

        try:
            status_code, data = subtitle_api.batch_edit_subtitle(
                project_id,
                subtitle_list=[edit_item],
            )
            assert status_code == 200
            assert data["success"] is True
            assert data["code"] == 0

            updated_status, updated_data = subtitle_api.wait_for_subtitle_text_updated(
                project_id,
                subtitle_id=subtitle_id,
                expected_texts=expected_texts,
                subtitle_type=1,
                timeout=30,
                interval=2,
            )
            assert updated_status == 200
            assert updated_data["success"] is True

            updated_subtitle = subtitle_api.find_subtitle_item(
                updated_data,
                subtitle_id=subtitle_id,
                subtitle_type=1,
            )
            assert updated_subtitle is not None
            assert subtitle_api.extract_segment_texts(updated_subtitle) == expected_texts
        finally:
            restore_item = subtitle_api.build_batch_edit_item(target_subtitle, edited_texts=original_texts)
            restore_status, restore_data = subtitle_api.batch_edit_subtitle(
                project_id,
                subtitle_list=[restore_item],
            )
            assert restore_status == 200
            assert restore_data["success"] is True

            reverted_status, reverted_data = subtitle_api.wait_for_subtitle_text_updated(
                project_id,
                subtitle_id=subtitle_id,
                expected_texts=original_texts,
                subtitle_type=1,
                timeout=30,
                interval=2,
            )
            assert reverted_status == 200
            assert reverted_data["success"] is True

    @allure.feature("加字幕")
    @allure.story("原文编辑后翻译")
    @allure.title("修改原文字幕后触发翻译并获取翻译结果")
    @pytest.mark.P0
    def test_edit_original_subtitle_and_translate(self):
        project_id = self._get_target_project_id()
        subtitle_api = ProjSubtitle()

        subtitle_status, subtitle_data = subtitle_api.wait_for_project_subtitle_ready(
            project_id,
            timeout=90,
            interval=3,
        )
        assert subtitle_status == 200
        assert subtitle_data["success"] is True

        target_original, target_translation = self._get_first_subtitle_pair(subtitle_data)
        subtitle_arr_id = target_original["subtitleArrId"]
        original_subtitle_id = target_original["id"]
        original_texts = subtitle_api.extract_segment_texts(target_original)
        previous_translation_texts = subtitle_api.extract_segment_texts(target_translation)
        assert original_texts
        assert previous_translation_texts

        edited_original_texts = self._build_original_edit_texts(original_texts)
        assert edited_original_texts != original_texts

        edit_item = subtitle_api.build_batch_edit_item(
            target_original,
            edited_texts=edited_original_texts,
            subtitle_type=0,
        )

        updated_translation_texts = None
        latest_original_item = target_original

        try:
            edit_status, edit_data = subtitle_api.batch_edit_subtitle(
                project_id,
                subtitle_list=[edit_item],
            )
            assert edit_status == 200
            assert edit_data["success"] is True
            assert edit_data["code"] == 0

            updated_ori_status, updated_ori_data = subtitle_api.wait_for_subtitle_text_updated(
                project_id,
                subtitle_id=original_subtitle_id,
                expected_texts=edited_original_texts,
                subtitle_type=0,
                timeout=30,
                interval=2,
            )
            assert updated_ori_status == 200
            assert updated_ori_data["success"] is True

            latest_original_item = subtitle_api.find_subtitle_item(
                updated_ori_data,
                subtitle_id=original_subtitle_id,
                subtitle_type=0,
            )
            assert latest_original_item is not None

            translate_status, translate_data = subtitle_api.subtitle_batch_translate(
                project_id,
                arr_ids=[subtitle_arr_id],
            )
            assert translate_status == 200
            assert translate_data["success"] is True
            assert translate_data["code"] == 0

            translated_status, translated_data = subtitle_api.wait_for_translation_result(
                project_id,
                subtitle_arr_id=subtitle_arr_id,
                expected_original_texts=edited_original_texts,
                previous_translation_texts=previous_translation_texts,
                timeout=120,
                interval=3,
            )
            assert translated_status == 200
            assert translated_data["success"] is True

            updated_translation = subtitle_api.find_subtitle_item(
                translated_data,
                subtitle_arr_id=subtitle_arr_id,
                subtitle_type=1,
            )
            assert updated_translation is not None
            assert updated_translation["isTranslating"] is False

            updated_translation_texts = subtitle_api.extract_segment_texts(updated_translation)
            assert updated_translation_texts
            assert updated_translation_texts != previous_translation_texts
        finally:
            restore_item = subtitle_api.build_batch_edit_item(
                latest_original_item,
                edited_texts=original_texts,
                subtitle_type=0,
            )
            restore_status, restore_data = subtitle_api.batch_edit_subtitle(
                project_id,
                subtitle_list=[restore_item],
            )
            assert restore_status == 200
            assert restore_data["success"] is True

            reverted_ori_status, reverted_ori_data = subtitle_api.wait_for_subtitle_text_updated(
                project_id,
                subtitle_id=original_subtitle_id,
                expected_texts=original_texts,
                subtitle_type=0,
                timeout=30,
                interval=2,
            )
            assert reverted_ori_status == 200
            assert reverted_ori_data["success"] is True

            if updated_translation_texts:
                revert_translate_status, revert_translate_data = subtitle_api.subtitle_batch_translate(
                    project_id,
                    arr_ids=[subtitle_arr_id],
                )
                assert revert_translate_status == 200
                assert revert_translate_data["success"] is True

                reverted_translation_status, reverted_translation_data = subtitle_api.wait_for_translation_result(
                    project_id,
                    subtitle_arr_id=subtitle_arr_id,
                    expected_original_texts=original_texts,
                    previous_translation_texts=updated_translation_texts,
                    timeout=120,
                    interval=3,
                )
                assert reverted_translation_status == 200
                assert reverted_translation_data["success"] is True

    @allure.feature("加字幕")
    @allure.story("新增原文后翻译")
    @allure.title("新增原文字幕并触发翻译")
    @pytest.mark.P0
    def test_add_new_subtitle_and_translate(self):
        project_id = self._get_target_project_id()
        subtitle_api = ProjSubtitle()

        subtitle_status, subtitle_data = subtitle_api.wait_for_project_subtitle_ready(
            project_id,
            timeout=90,
            interval=3,
        )
        assert subtitle_status == 200
        assert subtitle_data["success"] is True

        insert_plan = subtitle_api.plan_new_subtitle_slot(
            subtitle_data["data"]["oriList"],
            min_gap=500,
        )
        subtitle_arr_id = subtitle_api.generate_client_id()
        add_payload = subtitle_api.build_add_subtitle_payload(
            insert_plan["previous_item"],
            subtitle_arr_id=subtitle_arr_id,
            start_time=insert_plan["start_time"],
            duration=insert_plan["duration"],
        )
        new_original_text = f"Codex added subtitle {subtitle_arr_id}"
        should_cleanup = False

        try:
            add_status, add_data = subtitle_api.add_new_subtitle(
                project_id,
                **add_payload,
            )
            assert add_status == 200
            assert add_data["success"] is True
            assert add_data["code"] == 0
            should_cleanup = True

            created_status, created_data = subtitle_api.wait_for_subtitle_created(
                project_id,
                subtitle_arr_id=subtitle_arr_id,
                timeout=30,
                interval=2,
            )
            assert created_status == 200
            assert created_data["success"] is True

            created_original = subtitle_api.find_subtitle_item(
                created_data,
                subtitle_arr_id=subtitle_arr_id,
                subtitle_type=0,
            )
            created_translation = subtitle_api.find_subtitle_item(
                created_data,
                subtitle_arr_id=subtitle_arr_id,
                subtitle_type=1,
            )
            assert created_original is not None
            assert created_translation is not None

            initial_translation_texts = subtitle_api.extract_segment_texts(created_translation)

            edit_item = subtitle_api.build_batch_edit_item(
                created_original,
                edited_texts=[new_original_text],
                subtitle_type=0,
            )
            edit_status, edit_data = subtitle_api.batch_edit_subtitle(
                project_id,
                subtitle_list=[edit_item],
            )
            assert edit_status == 200
            assert edit_data["success"] is True
            assert edit_data["code"] == 0

            updated_ori_status, updated_ori_data = subtitle_api.wait_for_subtitle_text_updated(
                project_id,
                subtitle_id=created_original["id"],
                expected_texts=[new_original_text],
                subtitle_type=0,
                timeout=30,
                interval=2,
            )
            assert updated_ori_status == 200
            assert updated_ori_data["success"] is True

            translate_status, translate_data = subtitle_api.subtitle_batch_translate(
                project_id,
                arr_ids=[subtitle_arr_id],
            )
            assert translate_status == 200
            assert translate_data["success"] is True
            assert translate_data["code"] == 0

            translated_status, translated_data = subtitle_api.wait_for_translation_result(
                project_id,
                subtitle_arr_id=subtitle_arr_id,
                expected_original_texts=[new_original_text],
                previous_translation_texts=initial_translation_texts,
                timeout=120,
                interval=3,
            )
            assert translated_status == 200
            assert translated_data["success"] is True

            updated_translation = subtitle_api.find_subtitle_item(
                translated_data,
                subtitle_arr_id=subtitle_arr_id,
                subtitle_type=1,
            )
            assert updated_translation is not None
            assert updated_translation["isTranslating"] is False
            assert any(subtitle_api.extract_segment_texts(updated_translation))
        finally:
            if should_cleanup:
                delete_status, delete_data = subtitle_api.delete_subtitle(
                    project_id,
                    subtitle_arr_id=subtitle_arr_id,
                )
                assert delete_status == 200
                assert delete_data["success"] is True

                deleted_status, deleted_data = subtitle_api.wait_for_subtitle_deleted(
                    project_id,
                    subtitle_arr_id=subtitle_arr_id,
                    timeout=30,
                    interval=2,
                )
                assert deleted_status == 200
                assert deleted_data["success"] is True

    @allure.feature("加字幕")
    @allure.story("字幕显示切换")
    @allure.title("切换字幕原文、译文、双语和关闭")
    @pytest.mark.P0
    def test_update_subtitle_show(self):
        project_id = self._get_target_project_id()
        subtitle_api = ProjSubtitle()
        detail_api = ProjCreate()

        expected_show_values = {
            0: 0,
            1: 1,
            2: 2,
            3: 3,
        }

        try:
            for subtitle_show_enum, expected_show in expected_show_values.items():
                status_code, data = subtitle_api.update_subtitle_show(project_id, subtitle_show_enum)
                assert status_code == 200
                assert data["success"] is True
                assert data["code"] == 0

                detail_status, detail_data = subtitle_api.wait_for_subtitle_show_updated(
                    project_id,
                    subtitle_show_enum,
                    timeout=30,
                    interval=2,
                )
                assert detail_status == 200
                assert detail_data["success"] is True
                assert detail_data["data"]["subtitleShow"] == expected_show

            subtitle_status, subtitle_data = subtitle_api.get_project_subtitle(project_id)
            assert subtitle_status == 200
            assert subtitle_data["success"] is True
        finally:
            restore_status, restore_data = subtitle_api.update_subtitle_show(project_id, 3)
            assert restore_status == 200
            assert restore_data["success"] is True

            restored_detail_status, restored_detail_data = detail_api.get_project_detail(project_id)
            assert restored_detail_status == 200
            assert restored_detail_data["success"] is True
            assert restored_detail_data["data"]["subtitleShow"] == 3

    @allure.feature("加字幕")
    @allure.story("字幕设置")
    @allure.title("更新项目 CPL 字符数")
    @pytest.mark.P0
    def test_update_char_num(self):
        project_id = self._get_target_project_id()
        subtitle_api = ProjSubtitle()
        detail_api = ProjCreate()

        detail_status, detail_data = detail_api.get_project_detail(project_id)
        assert detail_status == 200
        assert detail_data["success"] is True

        detail_payload = detail_data.get("data", {})
        detail_has_char_num = detail_payload.get("charNum") is not None
        # Backend may omit charNum from project detail; fall back to the product default for restore.
        original_char_num = subtitle_api.normalize_char_num(detail_payload.get("charNum", 60))
        target_char_num = 99 if original_char_num != 99 else 60

        try:
            status_code, data = subtitle_api.update_char_num(project_id, target_char_num)
            assert status_code == 200
            assert data["success"] is True
            assert data["code"] == 0

            if detail_has_char_num:
                updated_status, updated_data = subtitle_api.wait_for_char_num_updated(
                    project_id,
                    target_char_num,
                    timeout=30,
                    interval=2,
                )
                assert updated_status == 200
                assert updated_data["success"] is True
                assert subtitle_api.normalize_char_num(updated_data["data"]["charNum"]) == target_char_num
            else:
                latest_detail_status, latest_detail_data = detail_api.get_project_detail(project_id)
                assert latest_detail_status == 200
                assert latest_detail_data["success"] is True
        finally:
            if original_char_num != target_char_num:
                restore_status, restore_data = subtitle_api.update_char_num(project_id, original_char_num)
                assert restore_status == 200
                assert restore_data["success"] is True
                assert restore_data["code"] == 0

                if detail_has_char_num:
                    restored_status, restored_data = subtitle_api.wait_for_char_num_updated(
                        project_id,
                        original_char_num,
                        timeout=30,
                        interval=2,
                    )
                    assert restored_status == 200
                    assert restored_data["success"] is True
                    assert subtitle_api.normalize_char_num(restored_data["data"]["charNum"]) == original_char_num
                else:
                    latest_detail_status, latest_detail_data = detail_api.get_project_detail(project_id)
                    assert latest_detail_status == 200
                    assert latest_detail_data["success"] is True

    @allure.feature("Add Subtitle")
    @allure.story("Subtitle Style")
    @allure.title("Batch Switch Font Styles")
    @pytest.mark.P0
    def test_batch_style_fonts(self):
        project_id = self._get_target_project_id()
        subtitle_api = ProjSubtitle()
        detail_api = ProjCreate()

        subtitle_status, subtitle_data = subtitle_api.wait_for_project_subtitle_ready(
            project_id,
            timeout=90,
            interval=3,
        )
        assert subtitle_status == 200
        assert subtitle_data["success"] is True

        target_translation = self._get_ready_translation_item(subtitle_data)
        if target_translation is None:
            pytest.skip("No ready translated subtitle was found for font style update")

        subtitle_arr_id = target_translation.get("subtitleArrId")
        assert subtitle_arr_id is not None

        style_status, style_data = detail_api.get_project_style(project_id)
        assert style_status == 200
        assert style_data["success"] is True

        target_style_item = subtitle_api.find_style_item(
            style_data,
            subtitle_arr_id=subtitle_arr_id,
            subtitle_type=1,
        )
        if target_style_item is None:
            target_style_item = {
                "subtitleArrId": subtitle_arr_id,
                "subtitleType": 1,
                "style": {},
            }

        original_style = copy.deepcopy(target_style_item["style"])
        original_style_fields = {
            key: original_style.get(key)
            for key in STYLE_VERIFY_KEYS
            if original_style.get(key) is not None
        }
        font_style_cases = load_font_style_cases(default_cases=FONT_STYLE_CASES)
        candidate_styles = [
            style_case
            for style_case in font_style_cases
            if any(original_style.get(key) != value for key, value in style_case.items())
        ]
        if not candidate_styles:
            pytest.skip("No alternative test fonts are available for the current project style")

        latest_style_item = copy.deepcopy(target_style_item)

        try:
            for style_case in candidate_styles:
                expected_fields = subtitle_api.normalize_style_match_fields(style_case)
                style_item = subtitle_api.build_batch_style_item(
                    latest_style_item,
                    style_updates=style_case,
                    subtitle_arr_id=subtitle_arr_id,
                )

                status_code, data = subtitle_api.batch_style(
                    project_id,
                    subtitle_type=1,
                    style_list=[style_item],
                )
                assert status_code == 200
                assert data["success"] is True
                assert data["code"] == 0

                updated_status, updated_data = subtitle_api.wait_for_style_updated(
                    project_id,
                    subtitle_arr_id=subtitle_arr_id,
                    expected_style_fields=expected_fields,
                    subtitle_type=1,
                    timeout=30,
                    interval=2,
                )
                assert updated_status == 200
                assert updated_data["success"] is True

                latest_style_item = subtitle_api.find_style_item(
                    updated_data,
                    subtitle_arr_id=subtitle_arr_id,
                    subtitle_type=1,
                )
                assert latest_style_item is not None
                for key, value in expected_fields.items():
                    assert latest_style_item["style"].get(key) == value
        finally:
            if original_style_fields:
                restore_item = subtitle_api.build_batch_style_item(
                    latest_style_item,
                    style_updates=original_style,
                    subtitle_arr_id=subtitle_arr_id,
                )
            else:
                restore_item = {
                    "subtitleArrId": subtitle_arr_id,
                    "style": {},
                }

            restore_status, restore_data = subtitle_api.batch_style(
                project_id,
                subtitle_type=1,
                style_list=[restore_item],
            )
            assert restore_status == 200
            assert restore_data["success"] is True
            assert restore_data["code"] == 0

            restored_status, restored_data = subtitle_api.wait_for_style_updated(
                project_id,
                subtitle_arr_id=subtitle_arr_id,
                expected_style_fields=original_style_fields,
                subtitle_type=1,
                timeout=30,
                interval=2,
            )
            assert restored_status == 200
            assert restored_data["success"] is True

    @allure.feature("加字幕")
    @allure.story("删除字幕")
    @allure.title("删除新增字幕-正常场景")
    @pytest.mark.P0
    def test_delete_new_subtitle(self):
        project_id = self._get_target_project_id()
        subtitle_api = ProjSubtitle()

        subtitle_status, subtitle_data = subtitle_api.wait_for_project_subtitle_ready(
            project_id,
            timeout=90,
            interval=3,
        )
        assert subtitle_status == 200
        assert subtitle_data["success"] is True

        insert_plan = subtitle_api.plan_new_subtitle_slot(
            subtitle_data["data"]["oriList"],
            min_gap=500,
        )
        subtitle_arr_id = subtitle_api.generate_client_id()
        add_payload = subtitle_api.build_add_subtitle_payload(
            insert_plan["previous_item"],
            subtitle_arr_id=subtitle_arr_id,
            start_time=insert_plan["start_time"],
            duration=insert_plan["duration"],
        )
        should_cleanup = False

        try:
            add_status, add_data = subtitle_api.add_new_subtitle(
                project_id,
                **add_payload,
            )
            assert add_status == 200
            assert add_data["success"] is True
            assert add_data["code"] == 0
            should_cleanup = True

            created_status, created_data = subtitle_api.wait_for_subtitle_created(
                project_id,
                subtitle_arr_id=subtitle_arr_id,
                timeout=30,
                interval=2,
            )
            assert created_status == 200
            assert created_data["success"] is True

            created_original = subtitle_api.find_subtitle_item(
                created_data,
                subtitle_arr_id=subtitle_arr_id,
                subtitle_type=0,
            )
            created_translation = subtitle_api.find_subtitle_item(
                created_data,
                subtitle_arr_id=subtitle_arr_id,
                subtitle_type=1,
            )
            assert created_original is not None
            assert created_translation is not None

            delete_status, delete_data = subtitle_api.delete_subtitle(
                project_id,
                subtitle_arr_id=subtitle_arr_id,
            )
            assert delete_status == 200
            assert delete_data["success"] is True
            assert delete_data["code"] == 0

            deleted_status, deleted_data = subtitle_api.wait_for_subtitle_deleted(
                project_id,
                subtitle_arr_id=subtitle_arr_id,
                timeout=30,
                interval=2,
            )
            assert deleted_status == 200
            assert deleted_data["success"] is True

            deleted_original = subtitle_api.find_subtitle_item(
                deleted_data,
                subtitle_arr_id=subtitle_arr_id,
                subtitle_type=0,
            )
            deleted_translation = subtitle_api.find_subtitle_item(
                deleted_data,
                subtitle_arr_id=subtitle_arr_id,
                subtitle_type=1,
            )
            assert deleted_original is None
            assert deleted_translation is None
            should_cleanup = False
        finally:
            if should_cleanup:
                subtitle_api.delete_subtitle(
                    project_id,
                    subtitle_arr_id=subtitle_arr_id,
                )
                subtitle_api.wait_for_subtitle_deleted(
                    project_id,
                    subtitle_arr_id=subtitle_arr_id,
                    timeout=30,
                    interval=2,
                )
