import copy

import allure
import pytest

from api_moudle.project.add_subtitle.add_subtitle_create import ProjCreate
from api_moudle.project.add_subtitle.add_subtitle_subtitle import ProjSubtitle
from api_moudle.project.add_subtitle.add_subtitle_timeline import Timeline
from api_moudle.project.home.proj_list import ProjList
from common.yaml_util import read_yaml, write_yaml


@allure.epic("AddSubtitle")
class TestTimeline:
    @staticmethod
    def _is_available_timeline_project(project_id, require_subtitles=False):
        timeline_api = Timeline()
        source_status, source_data = timeline_api.get_project_source(project_id)
        detail_status, detail_data = ProjCreate().get_project_detail(project_id)
        if not (
            source_status == 200
            and detail_status == 200
            and source_data.get("success") is True
            and detail_data.get("success") is True
            and timeline_api.find_video_detail(source_data) is not None
        ):
            return False

        if not require_subtitles:
            return True

        subtitle_status, subtitle_data = ProjSubtitle().get_project_subtitle(project_id)
        return (
            subtitle_status == 200
            and subtitle_data.get("success") is True
            and bool(subtitle_data.get("data", {}).get("oriList"))
        )

    @staticmethod
    def _get_target_project_id(require_subtitles=False):
        status_code, proj_data = ProjList().get_proj_list(pageSize=50)
        assert status_code == 200
        rows = proj_data["data"]["rows"]
        assert rows

        preferred_project_keys = (
            "subtitle_project_id",
            "timeline_project_id",
            "uploaded_video_project_id",
            "created_project_id",
            "test_project_id",
        )
        for key in preferred_project_keys:
            project_id = read_yaml(key, default=None)
            if project_id is None:
                continue
            for project in rows:
                if project["id"] == project_id and TestTimeline._is_available_timeline_project(
                    project_id,
                    require_subtitles=require_subtitles,
                ):
                    write_yaml({"timeline_project_id": project_id})
                    return project_id

        for project in sorted(rows, key=lambda item: int(item["id"]), reverse=True):
            project_id = project["id"]
            if TestTimeline._is_available_timeline_project(
                project_id,
                require_subtitles=require_subtitles,
            ):
                write_yaml({"timeline_project_id": project_id})
                return project_id

        latest_project = max(rows, key=lambda project: int(project["id"]))
        return latest_project["id"]

    @staticmethod
    def _build_subtitle_drag_plan(subtitle_data, min_shift=35000, max_shift=35000):
        subtitle_items = sorted(
            subtitle_data["data"]["oriList"],
            key=lambda item: float(item.get("startTime") or 0),
        )
        if len(subtitle_items) < 2:
            return None

        for index, subtitle_item in enumerate(subtitle_items):
            current_start_time = float(subtitle_item.get("startTime") or 0)
            current_end_time = float(ProjSubtitle.estimate_subtitle_end_time(subtitle_item))

            if index + 1 < len(subtitle_items):
                next_start_time = float(subtitle_items[index + 1].get("startTime") or current_end_time)
                forward_gap = next_start_time - current_end_time
                if forward_gap >= min_shift:
                    shift = min(max_shift, max(min_shift, int(forward_gap // 2)))
                    return {
                        "subtitle_item": copy.deepcopy(subtitle_item),
                        "expected_start_time": Timeline.normalize_start_time(current_start_time + shift),
                    }

            if index > 0:
                previous_end_time = float(ProjSubtitle.estimate_subtitle_end_time(subtitle_items[index - 1]))
                backward_gap = current_start_time - previous_end_time
                if backward_gap >= min_shift:
                    shift = min(max_shift, max(min_shift, int(backward_gap // 2)))
                    return {
                        "subtitle_item": copy.deepcopy(subtitle_item),
                        "expected_start_time": Timeline.normalize_start_time(current_start_time - shift),
                    }

        return None

    @allure.feature("Add Subtitle Timeline")
    @allure.story("Video Visibility")
    @allure.title("Toggle timeline video visibility")
    @pytest.mark.P0
    def test_update_video_visible_toggle(self):
        project_id = self._get_target_project_id()
        timeline_api = Timeline()

        source_status, source_data = timeline_api.get_project_source(project_id)
        assert source_status == 200
        assert source_data["success"] is True

        original_video_detail = timeline_api.find_video_detail(source_data)
        assert original_video_detail is not None
        original_video_detail = dict(original_video_detail)
        original_visible = original_video_detail["hideOrMute"]
        latest_video_detail = dict(original_video_detail)

        try:
            close_item = timeline_api.build_update_video_item(latest_video_detail, visible=False)
            close_status, close_data = timeline_api.update_video(project_id, video_list=[close_item])
            assert close_status == 200
            assert close_data["success"] is True
            assert close_data["code"] == 0

            closed_status, closed_data = timeline_api.wait_for_video_visible_updated(
                project_id,
                visible=False,
                video_id=original_video_detail["id"],
                timeout=30,
                interval=2,
            )
            assert closed_status == 200
            assert closed_data["success"] is True

            latest_video_detail = timeline_api.find_video_detail(closed_data, video_id=original_video_detail["id"])
            assert latest_video_detail is not None
            assert latest_video_detail["hideOrMute"] is False

            open_item = timeline_api.build_update_video_item(latest_video_detail, visible=True)
            open_status, open_data = timeline_api.update_video(project_id, video_list=[open_item])
            assert open_status == 200
            assert open_data["success"] is True
            assert open_data["code"] == 0

            opened_status, opened_data = timeline_api.wait_for_video_visible_updated(
                project_id,
                visible=True,
                video_id=original_video_detail["id"],
                timeout=30,
                interval=2,
            )
            assert opened_status == 200
            assert opened_data["success"] is True

            latest_video_detail = timeline_api.find_video_detail(opened_data, video_id=original_video_detail["id"])
            assert latest_video_detail is not None
            assert latest_video_detail["hideOrMute"] is True
        finally:
            restore_item = timeline_api.build_update_video_item(latest_video_detail, visible=original_visible)
            restore_status, restore_data = timeline_api.update_video(project_id, video_list=[restore_item])
            assert restore_status == 200
            assert restore_data["success"] is True

            restored_status, restored_data = timeline_api.wait_for_video_visible_updated(
                project_id,
                visible=original_visible,
                video_id=original_video_detail["id"],
                timeout=30,
                interval=2,
            )
            assert restored_status == 200
            assert restored_data["success"] is True

    @allure.feature("Add Subtitle Timeline")
    @allure.story("Drag Subtitle")
    @allure.title("Drag original subtitle on timeline")
    @pytest.mark.P0
    def test_drag_original_subtitle(self):
        project_id = self._get_target_project_id(require_subtitles=True)
        timeline_api = Timeline()
        subtitle_api = ProjSubtitle()

        subtitle_status, subtitle_data = subtitle_api.wait_for_project_subtitle_ready(
            project_id,
            timeout=90,
            interval=3,
        )
        assert subtitle_status == 200
        assert subtitle_data["success"] is True

        drag_plan = self._build_subtitle_drag_plan(subtitle_data)
        if drag_plan is None:
            pytest.skip("No subtitle with a safe timeline gap was found for drag validation")

        original_subtitle = drag_plan["subtitle_item"]
        subtitle_id = original_subtitle["id"]
        original_start_time = Timeline.normalize_start_time(original_subtitle["startTime"])
        expected_start_time = drag_plan["expected_start_time"]
        latest_subtitle = copy.deepcopy(original_subtitle)
        should_restore = False

        try:
            drag_item = timeline_api.build_drag_subtitle_item(
                latest_subtitle,
                start_time=expected_start_time,
                subtitle_type=0,
            )
            drag_status, drag_data = timeline_api.drag_subtitle(project_id, subtitle_list=[drag_item])
            assert drag_status == 200
            assert drag_data["success"] is True
            assert drag_data["code"] == 0
            should_restore = True

            updated_status, updated_data = timeline_api.wait_for_subtitle_start_time_updated(
                project_id,
                subtitle_id=subtitle_id,
                expected_start_time=expected_start_time,
                subtitle_type=0,
                timeout=30,
                interval=2,
            )
            assert updated_status == 200
            assert updated_data["success"] is True

            latest_subtitle = timeline_api.find_subtitle_item(
                updated_data,
                subtitle_id=subtitle_id,
                subtitle_type=0,
            )
            assert latest_subtitle is not None
            assert timeline_api.start_time_matches(latest_subtitle["startTime"], expected_start_time)
        finally:
            if should_restore:
                restore_item = timeline_api.build_drag_subtitle_item(
                    latest_subtitle,
                    start_time=original_start_time,
                    subtitle_type=0,
                )
                restore_status, restore_data = timeline_api.drag_subtitle(
                    project_id,
                    subtitle_list=[restore_item],
                )
                assert restore_status == 200
                assert restore_data["success"] is True

                restored_status, restored_data = timeline_api.wait_for_subtitle_start_time_updated(
                    project_id,
                    subtitle_id=subtitle_id,
                    expected_start_time=original_start_time,
                    subtitle_type=0,
                    timeout=30,
                    interval=2,
                )
                assert restored_status == 200
                assert restored_data["success"] is True