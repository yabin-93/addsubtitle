import copy

import allure
import pytest

from api_moudle.project.add_subtitle.add_subtitle_create import ProjCreate
from api_moudle.project.home.proj_list import ProjList
from api_moudle.project.add_subtitle.add_subtitle_subtitle import ProjSubtitle
from common.yaml_util import read_yaml, write_yaml


@allure.epic("字幕")
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
        raise AssertionError("未找到可用的原文/译文字幕对")

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

    @allure.feature("字幕管理")
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

    @allure.feature("字幕管理")
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

    @allure.feature("字幕管理")
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

    @allure.feature("字幕管理")
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

    @allure.feature("字幕管理")
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

    @allure.feature("字幕管理")
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
