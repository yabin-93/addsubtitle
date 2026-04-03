import time

from api_moudle.project.add_subtitle.add_subtitle_create import ProjCreate
from common.test_data_paths import VIDEO_DIR
from common.yaml_util import write_yaml


class TranslateCreate(ProjCreate):
    YAML_PATH = "project/translate/translate_create.yaml"
    CUSTOM_VIDEO_PATH = r"E:\proj\test_data\upload_files\video\bbc.mp4"  # e.g. r"E:\proj\test_data\upload_files\video\bbc.mp4"
    DEFAULT_USAGE = 1
    DEFAULT_PROJECT_TYPE = 1
    DEFAULT_LANGUAGE = "English"
    DEFAULT_TRANSLATION_LANGUAGE = "Chinese"
    DEFAULT_LANGUAGE_CODE = "en"
    DEFAULT_TRANSLATION_LANGUAGE_CODE = "zh"
    DEFAULT_MODE = "translation"
    DEFAULT_GENERATE_SPEECH = True
    DEFAULT_USE_TRANSLATE = True
    DEFAULT_LIP_SYNC = False
    DEFAULT_PEOPLE_NUMBER = 0
    SUPPORTED_VIDEO_SUFFIXES = (".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm")

    @classmethod
    def get_default_video_path(cls):
        if cls.CUSTOM_VIDEO_PATH:
            return cls.resolve_video_path(cls.CUSTOM_VIDEO_PATH)

        for file_path in sorted(VIDEO_DIR.iterdir(), key=lambda path: path.name.lower()):
            if file_path.is_file() and file_path.suffix.lower() in cls.SUPPORTED_VIDEO_SUFFIXES:
                return file_path
        raise FileNotFoundError(f"no video file found in {VIDEO_DIR}")

    def get_video_pre_create_payload(self, video_path):
        video_path = self.resolve_video_path(video_path)
        media_info = self.get_media_info(video_path=video_path)
        duration_seconds = float(media_info.get("format", {}).get("duration", 0) or 0)
        if duration_seconds <= 0:
            raise RuntimeError(f"invalid video duration: {video_path}")
        return {
            "video_path": video_path,
            "duration": duration_seconds * 1000,
            "asset_size": video_path.stat().st_size,
        }

    def create_translation_upload_task(self, file_path=None, cookie=None, part_size=None, category="video"):
        file_path = self.resolve_upload_path(category, file_path=file_path)
        return self.run_authed_request(
            self.YAML_PATH,
            "create_translation_upload_task",
            cookie=cookie,
            ext=file_path.name,
            asset_size=file_path.stat().st_size,
            parts=self.get_upload_part_count(file_path.stat().st_size, part_size=part_size),
        )

    def pre_create_project(
        self,
        duration=30696.78,
        asset_size=7523986,
        usage=DEFAULT_USAGE,
        device=None,
        device_type="desktop",
        cookie=None,
    ):
        return self.run_authed_request(
            self.YAML_PATH,
            "pre_create_project",
            cookie=cookie,
            duration=duration,
            asset_size=asset_size,
            usage=usage,
            device=device or self.DEFAULT_DEVICE,
            device_type=device_type,
        )

    def conform_event(self, event_type, message="", project_id=None, cookie=None):
        api_name = "event_conform_with_project" if project_id is not None else "event_conform"
        kwargs = {"event_type": event_type, "message": message}
        if project_id is not None:
            kwargs["project_id"] = project_id
        return self.run_authed_request(
            self.YAML_PATH,
            api_name,
            cookie=cookie,
            **kwargs,
        )

    def create_project(
        self,
        name,
        project_id,
        temp_id=None,
        project_type=DEFAULT_PROJECT_TYPE,
        usage=DEFAULT_USAGE,
        language=DEFAULT_LANGUAGE,
        translation_language=DEFAULT_TRANSLATION_LANGUAGE,
        people_number=DEFAULT_PEOPLE_NUMBER,
        lip_sync=DEFAULT_LIP_SYNC,
        generate_speech=DEFAULT_GENERATE_SPEECH,
        use_translate=DEFAULT_USE_TRANSLATE,
        mode=DEFAULT_MODE,
        language_code=DEFAULT_LANGUAGE_CODE,
        translation_language_code=DEFAULT_TRANSLATION_LANGUAGE_CODE,
        cookie=None,
    ):
        return self.run_authed_request(
            self.YAML_PATH,
            "create_project",
            cookie=cookie,
            name=name,
            project_id=project_id,
            temp_id=temp_id or int(time.time() * 1000),
            project_type=project_type,
            usage=usage,
            language=language,
            translation_language=translation_language,
            people_number=people_number,
            lip_sync=lip_sync,
            generate_speech=generate_speech,
            use_translate=use_translate,
            mode=mode,
            language_code=language_code,
            translation_language_code=translation_language_code,
        )

    def get_project_detail(self, project_id, cookie=None):
        return self.run_authed_request(
            self.YAML_PATH,
            "get_project_detail",
            cookie=cookie,
            project_id=project_id,
        )

    def get_project_status(self, project_id, cookie=None):
        return self.run_authed_request(
            self.YAML_PATH,
            "get_project_status",
            cookie=cookie,
            project_id=project_id,
        )

    def get_project_source(self, project_id, cookie=None):
        return self.run_authed_request(
            self.YAML_PATH,
            "get_project_source",
            cookie=cookie,
            project_id=project_id,
        )

    def get_project_speaker_info(self, project_id, cookie=None):
        return self.run_authed_request(
            self.YAML_PATH,
            "get_project_speaker_info",
            cookie=cookie,
            project_id=project_id,
        )

    def create_project_flow(self, name=None, cookie=None, video_path=None, image_path=None, audio_path=None):
        pre_create_kwargs = {}
        if video_path is not None:
            video_payload = self.get_video_pre_create_payload(video_path)
            video_path = video_payload["video_path"]
            pre_create_kwargs = {
                "duration": video_payload["duration"],
                "asset_size": video_payload["asset_size"],
            }

        project_name = self.build_project_name(name=name, video_path=video_path)
        pre_status, pre_data = self.pre_create_project(cookie=cookie, **pre_create_kwargs)
        if pre_status != 200 or pre_data.get("success") is not True:
            return [pre_status, {"stage": "pre_create_project", "data": pre_data}]

        project_id = pre_data["data"]["projectId"]
        event_status, event_data = self.conform_event("project_create", cookie=cookie)
        if event_status != 200 or event_data.get("success") is not True:
            return [event_status, {"stage": "event_conform", "projectId": project_id, "data": event_data}]

        temp_id = int(time.time() * 1000)
        create_status, create_data = self.create_project(
            name=project_name,
            project_id=project_id,
            temp_id=temp_id,
            cookie=cookie,
        )
        if create_status == 200 and create_data.get("success") is True:
            write_yaml(
                {
                    "translate_created_project_id": project_id,
                    "translate_created_temp_id": temp_id,
                    "translate_test_project_id": project_id,
                }
            )

        flow_data = {
            "projectId": project_id,
            "projectName": project_name,
            "tempId": temp_id,
            "preCreate": pre_data,
            "eventConform": event_data,
            "create": create_data,
        }

        if create_status != 200 or create_data.get("success") is not True:
            return [create_status, flow_data]

        if video_path is not None:
            bootstrap_status, bootstrap_data = self.bootstrap_project_editing(project_id, cookie=cookie)
            flow_data["editingEvents"] = bootstrap_data
            if bootstrap_status != 200:
                return [bootstrap_status, flow_data]

            if image_path is None:
                image_path = self.generate_thumbnail_from_video(video_path=video_path)
                flow_data["generatedThumbnailPath"] = str(image_path)

            if audio_path is None:
                audio_path = self.extract_audio_from_video(video_path=video_path)
                if audio_path is not None:
                    flow_data["generatedAudioPath"] = str(audio_path)

            upload_status, upload_data = self.upload_video(project_id, file_path=video_path, cookie=cookie)
            flow_data["uploadVideo"] = upload_data
            if upload_status != 200 or upload_data.get("complete", {}).get("success") is not True:
                return [upload_status, flow_data]

        if image_path is not None:
            upload_status, upload_data = self.upload_thumbnail(project_id, file_path=image_path, cookie=cookie)
            flow_data["uploadThumbnail"] = upload_data
            if upload_status != 200 or upload_data.get("complete", {}).get("success") is not True:
                return [upload_status, flow_data]

        if audio_path is not None:
            upload_status, upload_data = self.upload_audio(project_id, file_path=audio_path, cookie=cookie)
            flow_data["uploadAudio"] = upload_data
            if upload_status != 200 or upload_data.get("complete", {}).get("success") is not True:
                return [upload_status, flow_data]

        if video_path is not None:
            ready_status, ready_data = self.wait_for_project_media_ready(
                project_id,
                require_thumbnail=image_path is not None,
                cookie=cookie,
            )
            flow_data["projectReady"] = ready_data
            if ready_status != 200:
                return [ready_status, flow_data]

        return [create_status, flow_data]
