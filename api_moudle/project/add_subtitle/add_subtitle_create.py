from pathlib import Path
import json
import subprocess
import time

import requests

from api_moudle.project.home.base_api import BaseApi
from common.auth_util import get_cookie
from common.logger import logger
from common.test_data_paths import (
    AUDIO_DIR,
    DEFAULT_AUDIO_FILE_NAME,
    DEFAULT_IMAGE_FILE_NAME,
    DEFAULT_VIDEO_FILE_NAME,
    IMAGE_DIR,
    TEMP_DIR,
    VIDEO_DIR,
    ensure_test_data_dirs,
    get_default_audio_path,
    get_default_image_path,
    get_default_video_path,
    require_upload_file,
)
from common.yaml_util import write_yaml


class ProjCreate(BaseApi):
    DEFAULT_DEVICE = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    CUSTOM_VIDEO_PATH = None  # e.g. r"E:\proj\test_data\upload_files\video\bbc.mp4"
    DEFAULT_UPLOAD_PART_SIZE = 5 * 1024 * 1024
    DEFAULT_UPLOAD_RETRY_COUNT = 3
    DEFAULT_UPLOAD_RETRY_DELAY = 2
    DEFAULT_VIDEO_DIR = VIDEO_DIR
    DEFAULT_AUDIO_DIR = AUDIO_DIR
    DEFAULT_IMAGE_DIR = IMAGE_DIR
    DEFAULT_TEMP_DIR = TEMP_DIR
    DEFAULT_VIDEO_FILE_NAME = DEFAULT_VIDEO_FILE_NAME
    DEFAULT_AUDIO_FILE_NAME = DEFAULT_AUDIO_FILE_NAME
    DEFAULT_IMAGE_FILE_NAME = DEFAULT_IMAGE_FILE_NAME

    @classmethod
    def get_default_video_path(cls):
        if cls.CUSTOM_VIDEO_PATH:
            return cls.resolve_video_path(cls.CUSTOM_VIDEO_PATH)
        return get_default_video_path()

    @staticmethod
    def get_default_audio_path():
        return get_default_audio_path()

    @staticmethod
    def get_default_image_path():
        return get_default_image_path()

    @staticmethod
    def build_project_name(name=None, video_path=None):
        if video_path is not None:
            return ProjCreate.resolve_video_path(video_path).stem
        if name:
            return name
        return f"Project {int(time.time())}"

    @staticmethod
    def resolve_output_path(category, file_path=None):
        default_paths = {
            "audio": get_default_audio_path(),
            "image": get_default_image_path(),
        }

        if category not in default_paths:
            raise ValueError(f"Unsupported output category: {category}")

        if file_path is None:
            file_path = default_paths[category]
        else:
            file_path = Path(file_path)
            if not file_path.is_absolute():
                if len(file_path.parts) == 1:
                    base_dir = AUDIO_DIR if category == "audio" else IMAGE_DIR
                    file_path = base_dir / file_path.name
                else:
                    file_path = Path.cwd() / file_path

        file_path.parent.mkdir(parents=True, exist_ok=True)
        return file_path

    @staticmethod
    def resolve_upload_path(category, file_path=None):
        default_names = {
            "video": DEFAULT_VIDEO_FILE_NAME,
            "audio": DEFAULT_AUDIO_FILE_NAME,
            "image": DEFAULT_IMAGE_FILE_NAME,
        }
        default_dirs = {
            "video": VIDEO_DIR,
            "audio": AUDIO_DIR,
            "image": IMAGE_DIR,
        }

        if category not in default_names:
            raise ValueError(f"Unsupported upload category: {category}")

        if file_path is None:
            return require_upload_file(category, default_names[category])

        file_path = Path(file_path)
        if not file_path.is_absolute():
            if len(file_path.parts) == 1:
                default_path = default_dirs[category] / file_path.name
                if default_path.exists():
                    file_path = default_path
                else:
                    file_path = Path.cwd() / file_path
            else:
                file_path = Path.cwd() / file_path

        if not file_path.exists():
            raise FileNotFoundError(f"{category} file not found: {file_path}")

        return file_path

    @staticmethod
    def resolve_video_path(file_path=None):
        return ProjCreate.resolve_upload_path("video", file_path=file_path)

    @staticmethod
    def resolve_audio_path(file_path=None):
        return ProjCreate.resolve_upload_path("audio", file_path=file_path)

    @staticmethod
    def resolve_image_path(file_path=None):
        return ProjCreate.resolve_upload_path("image", file_path=file_path)

    @classmethod
    def get_upload_part_count(cls, file_size, part_size=None):
        part_size = part_size or cls.DEFAULT_UPLOAD_PART_SIZE
        return (file_size + part_size - 1) // part_size

    @staticmethod
    def _run_media_command(command):
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"Command failed: {' '.join(command)}")
        return result

    def get_media_info(self, video_path=None):
        video_path = self.resolve_video_path(video_path)
        result = self._run_media_command(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=index,codec_type,codec_name,width,height",
                "-of",
                "json",
                str(video_path),
            ]
        )
        return json.loads(result.stdout)

    def has_audio_stream(self, video_path=None):
        media_info = self.get_media_info(video_path=video_path)
        return any(stream.get("codec_type") == "audio" for stream in media_info.get("streams", []))

    def build_thumbnail_timestamp(self, video_path=None):
        media_info = self.get_media_info(video_path=video_path)
        duration = float(media_info.get("format", {}).get("duration", 0) or 0)
        if duration <= 0:
            return "00:00:01"

        target_seconds = min(max(duration * 0.2, 1.0), max(duration - 0.1, 0.1))
        hours = int(target_seconds // 3600)
        minutes = int((target_seconds % 3600) // 60)
        seconds = target_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"

    def generate_thumbnail_from_video(self, video_path=None, image_path=None):
        video_path = self.resolve_video_path(video_path)
        image_path = self.resolve_output_path("image", image_path)
        timestamp = self.build_thumbnail_timestamp(video_path=video_path)
        self._run_media_command(
            [
                "ffmpeg",
                "-y",
                "-ss",
                timestamp,
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-update",
                "1",
                str(image_path),
            ]
        )
        return image_path

    def extract_audio_from_video(self, video_path=None, audio_path=None):
        video_path = self.resolve_video_path(video_path)
        if not self.has_audio_stream(video_path=video_path):
            logger.info(f"skip audio extraction because no audio stream exists: {video_path}")
            return None

        audio_path = self.resolve_output_path("audio", audio_path)
        self._run_media_command(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(video_path),
                "-vn",
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                str(audio_path),
            ]
        )
        return audio_path

    # 进入项目编辑态，补发编辑页需要的埋点事件。
    def bootstrap_project_editing(self, project_id, cookie=None):
        result = {}
        for event in ("project_edit", "loading_start"):
            status_code, data = self.conform_event(event, project_id=project_id, cookie=cookie)
            result[event] = {"status_code": status_code, "data": data}
            if status_code != 200 or data.get("success") is not True:
                return [status_code, result]
        return [200, result]

    # 创建媒体分片上传任务，返回 uploadId 和每个分片的 presigned URL。
    def create_translation_upload_task(self, file_path=None, cookie=None, part_size=None, category="video"):
        file_path = self.resolve_upload_path(category, file_path=file_path)
        return self.run_authed_request(
            "project/add_subtitle/add_subtitle_create.yaml",
            "create_translation_upload_task",
            cookie=cookie,
            ext=file_path.name,
            asset_size=file_path.stat().st_size,
            parts=self.get_upload_part_count(file_path.stat().st_size, part_size=part_size),
        )

    def _put_upload_part_with_retry(self, url, chunk, part_number, category):
        last_error = None
        for attempt in range(1, self.DEFAULT_UPLOAD_RETRY_COUNT + 1):
            try:
                response = requests.put(url, data=chunk, timeout=240)
                response.raise_for_status()
                etag = response.headers.get("ETag")
                if not etag:
                    raise RuntimeError(f"Missing ETag for uploaded part {part_number}")
                return etag
            except (requests.RequestException, RuntimeError) as e:
                last_error = e
                if attempt == self.DEFAULT_UPLOAD_RETRY_COUNT:
                    raise
                logger.warning(
                    f"upload_{category} part {part_number} failed on attempt {attempt}, retrying: {e}"
                )
                time.sleep(self.DEFAULT_UPLOAD_RETRY_DELAY)

        raise last_error

    def upload_parts_to_presigned_urls(self, file_path, urls, part_size=None, category="video"):
        file_path = self.resolve_upload_path(category, file_path=file_path)
        part_size = part_size or self.DEFAULT_UPLOAD_PART_SIZE
        expected_parts = self.get_upload_part_count(file_path.stat().st_size, part_size=part_size)

        if len(urls) != expected_parts:
            raise RuntimeError(f"Upload part count mismatch: expected {expected_parts}, got {len(urls)}")

        completed_parts = []
        with open(str(file_path), "rb") as f:
            for index, url in enumerate(urls, start=1):
                chunk = f.read(part_size)
                if not chunk:
                    raise RuntimeError(f"Missing upload chunk for part {index}")

                etag = self._put_upload_part_with_retry(url, chunk, index, category)
                completed_parts.append({"partNumber": index, "eTag": etag})

            if f.read(1):
                raise RuntimeError("Upload file still has unread bytes after all parts were uploaded")

        return completed_parts

    def _complete_project_file_upload(self, api_path, payload, cookie=None):
        last_response = None
        for attempt in range(1, self.DEFAULT_UPLOAD_RETRY_COUNT + 1):
            active_cookie = cookie or get_cookie(force_refresh=(attempt > 1 and cookie is None))
            headers = {"Content-Type": "application/json", "Cookie": active_cookie}
            response = self.request_api("post", api_path, json=payload, headers=headers)
            last_response = response

            if response and response[0] == 200:
                return response

            if cookie is None and response and response[0] == 401:
                logger.warning(f"project file upload callback got 401 on attempt {attempt}, refreshing cookie")
                continue

            if response and response[0] is None and attempt < self.DEFAULT_UPLOAD_RETRY_COUNT:
                logger.warning(f"project file upload callback failed on attempt {attempt}, retrying: {response[1]}")
                time.sleep(self.DEFAULT_UPLOAD_RETRY_DELAY)
                continue

            return response

        return last_response

    # 通知后端视频文件分片上传完成。
    def complete_video_upload(self, project_id, upload_id, completed_parts, z_index=0, cookie=None):
        payload = {
            "upload": {"uploadId": upload_id, "completedParts": completed_parts},
            "zIndex": z_index,
        }
        return self._complete_project_file_upload(
            f"/api/file/{project_id}/upload-video",
            payload,
            cookie=cookie,
        )

    # 通知后端音频文件分片上传完成。
    def complete_audio_upload(self, project_id, upload_id, completed_parts, z_index=0, cookie=None):
        payload = {
            "upload": {"uploadId": upload_id, "completedParts": completed_parts},
            "zIndex": z_index,
        }
        return self._complete_project_file_upload(
            f"/api/file/{project_id}/upload-audio-new",
            payload,
            cookie=cookie,
        )

    # 通知后端缩略图文件分片上传完成。
    def complete_thumbnail_upload(self, project_id, upload_id, completed_parts, cookie=None):
        payload = {"uploadId": upload_id, "completedParts": completed_parts}
        return self._complete_project_file_upload(
            f"/api/file/{project_id}/upload-thumbnail",
            payload,
            cookie=cookie,
        )

    def _upload_project_asset(
        self,
        project_id,
        file_path,
        category,
        complete_upload_func,
        include_z_index,
        z_index=0,
        cookie=None,
        part_size=None,
    ):
        file_path = self.resolve_upload_path(category, file_path=file_path)
        try:
            task_status, task_data = self.create_translation_upload_task(
                file_path=file_path,
                cookie=cookie,
                part_size=part_size,
                category=category,
            )
            if task_status != 200 or task_data.get("success") is not True:
                return [task_status, {"stage": "create_translation_upload_task", "data": task_data}]

            upload_id = task_data["data"]["uploadId"]
            urls = task_data["data"]["urls"]
            completed_parts = self.upload_parts_to_presigned_urls(
                file_path=file_path,
                urls=urls,
                part_size=part_size,
                category=category,
            )

            if include_z_index:
                complete_status, complete_data = complete_upload_func(
                    project_id=project_id,
                    upload_id=upload_id,
                    completed_parts=completed_parts,
                    z_index=z_index,
                    cookie=cookie,
                )
            else:
                complete_status, complete_data = complete_upload_func(
                    project_id=project_id,
                    upload_id=upload_id,
                    completed_parts=completed_parts,
                    cookie=cookie,
                )

            if complete_status == 200 and complete_data.get("success") is True:
                write_yaml(
                    {
                        f"uploaded_{category}_project_id": project_id,
                        f"uploaded_{category}_file_name": file_path.name,
                        f"uploaded_{category}_upload_id": upload_id,
                    }
                )

            return [
                complete_status,
                {
                    "filePath": str(file_path),
                    "uploadId": upload_id,
                    "completedParts": completed_parts,
                    "task": task_data,
                    "complete": complete_data,
                },
            ]
        except Exception as e:
            logger.error(f"upload_{category} failed: {e}")
            return [
                None,
                {"stage": f"upload_{category}", "error": f"upload_{category}_failed", "message": str(e)},
            ]

    # 完整执行视频上传流程：建任务、上传分片、回调后端。
    def upload_video(self, project_id, file_path=None, z_index=0, cookie=None, part_size=None):
        return self._upload_project_asset(
            project_id=project_id,
            file_path=file_path,
            category="video",
            complete_upload_func=self.complete_video_upload,
            include_z_index=True,
            z_index=z_index,
            cookie=cookie,
            part_size=part_size,
        )

    # 完整执行音频上传流程：建任务、上传分片、回调后端。
    def upload_audio(self, project_id, file_path=None, z_index=0, cookie=None, part_size=None):
        return self._upload_project_asset(
            project_id=project_id,
            file_path=file_path,
            category="audio",
            complete_upload_func=self.complete_audio_upload,
            include_z_index=True,
            z_index=z_index,
            cookie=cookie,
            part_size=part_size,
        )

    # 完整执行缩略图上传流程：建任务、上传分片、回调后端。
    def upload_thumbnail(self, project_id, file_path=None, cookie=None, part_size=None):
        return self._upload_project_asset(
            project_id=project_id,
            file_path=file_path,
            category="image",
            complete_upload_func=self.complete_thumbnail_upload,
            include_z_index=False,
            cookie=cookie,
            part_size=part_size,
        )

    # 轮询项目状态，等待视频上传结果在项目中生效。
    def wait_for_video_ready(self, project_id, cookie=None, timeout=30, interval=2):
        deadline = time.time() + timeout
        latest_status = None
        latest_source = None

        while time.time() < deadline:
            status_code, status_data = self.get_project_status(project_id, cookie=cookie)
            source_code, source_data = self.get_project_source(project_id, cookie=cookie)
            latest_status = {"status_code": status_code, "data": status_data}
            latest_source = {"status_code": source_code, "data": source_data}

            video_ready = (
                status_code == 200
                and source_code == 200
                and status_data.get("success") is True
                and source_data.get("success") is True
                and status_data["data"].get("videoUpload") is True
                and bool(source_data["data"].get("video", {}).get("url"))
            )
            if video_ready:
                return [200, {"status": status_data, "source": source_data}]

            time.sleep(interval)

        return [
            408,
            {
                "stage": "wait_for_video_ready",
                "status": latest_status,
                "source": latest_source,
            },
        ]

    # 轮询项目媒体状态，等待视频、雪碧图和可选缩略图都可访问。
    def wait_for_project_media_ready(self, project_id, require_thumbnail=False, cookie=None, timeout=60, interval=3):
        deadline = time.time() + timeout
        latest = {}

        while time.time() < deadline:
            status_code, status_data = self.get_project_status(project_id, cookie=cookie)
            source_code, source_data = self.get_project_source(project_id, cookie=cookie)
            detail_code, detail_data = self.get_project_detail(project_id, cookie=cookie)
            latest = {
                "status": {"status_code": status_code, "data": status_data},
                "source": {"status_code": source_code, "data": source_data},
                "detail": {"status_code": detail_code, "data": detail_data},
            }

            if not (
                status_code == 200
                and source_code == 200
                and detail_code == 200
                and status_data.get("success") is True
                and source_data.get("success") is True
                and detail_data.get("success") is True
            ):
                time.sleep(interval)
                continue

            status_payload = status_data["data"]
            source_payload = source_data["data"]
            detail_payload = detail_data["data"]
            video_url = source_payload.get("video", {}).get("url")
            sprite_url = source_payload.get("video", {}).get("vttUrl", "").replace("stream_1.vtt", "stream_1.jpg")
            thumbnail_url = detail_payload.get("thumbnail")

            media_ready = (
                status_payload.get("videoUpload") is True
                and status_payload.get("videoCompleted") is True
                and status_payload.get("sprite") is True
                and bool(video_url)
                and bool(sprite_url)
            )
            if require_thumbnail:
                media_ready = media_ready and bool(thumbnail_url)

            if not media_ready:
                time.sleep(interval)
                continue

            try:
                video_resp = requests.get(video_url, headers={"Range": "bytes=0-1023"}, timeout=20)
                sprite_resp = requests.get(sprite_url, timeout=20)
                thumbnail_resp = None
                if require_thumbnail:
                    thumbnail_resp = requests.get(thumbnail_url, timeout=20)
            except requests.RequestException:
                time.sleep(interval)
                continue

            resource_ready = (
                video_resp.status_code in (200, 206)
                and video_resp.headers.get("Content-Type") == "video/mp4"
                and sprite_resp.status_code == 200
                and sprite_resp.headers.get("Content-Type", "").startswith("image/jpeg")
            )
            if require_thumbnail:
                resource_ready = (
                    resource_ready
                    and thumbnail_resp is not None
                    and thumbnail_resp.status_code == 200
                    and thumbnail_resp.headers.get("Content-Type") == "image/png"
                )

            if resource_ready:
                latest["resources"] = {
                    "video_url": video_url,
                    "sprite_url": sprite_url,
                    "thumbnail_url": thumbnail_url,
                }
                return [200, latest]

            time.sleep(interval)

        return [408, {"stage": "wait_for_project_media_ready", "latest": latest}]

    # 预创建项目，向后端申请 projectId。
    def pre_create_project(
        self,
        duration=30696.78,
        asset_size=7523986,
        usage=2,
        device=None,
        device_type="desktop",
        cookie=None,
    ):
        try:
            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_create.yaml",
                "pre_create_project",
                cookie=cookie,
                duration=duration,
                asset_size=asset_size,
                usage=usage,
                device=device or self.DEFAULT_DEVICE,
                device_type=device_type,
            )
        except Exception as e:
            logger.error(f"pre_create_project failed: {e}")
            return [None, {"error": "pre_create_project_failed", "message": str(e)}]

    # 上报埋点事件，可用于 project_create、project_edit、loading_start 等场景。
    def conform_event(self, event_type, message="", project_id=None, cookie=None):
        try:
            api_name = "event_conform_with_project" if project_id is not None else "event_conform"
            kwargs = {"event_type": event_type, "message": message}
            if project_id is not None:
                kwargs["project_id"] = project_id
            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_create.yaml",
                api_name,
                cookie=cookie,
                **kwargs,
            )
        except Exception as e:
            logger.error(f"conform_event failed: {e}")
            return [None, {"error": "conform_event_failed", "message": str(e)}]

    # 正式创建“加字幕”项目，并设置语种、翻译语种、模式等参数。
    def create_project(
        self,
        name,
        project_id,
        temp_id=None,
        project_type=1,
        usage=2,
        language="English",
        translation_language="Chinese",
        people_number=0,
        lip_sync=False,
        generate_speech=False,
        use_translate=True,
        mode="add_subtitle",
        language_code="en",
        translation_language_code="zh",
        cookie=None,
    ):
        try:
            return self.run_authed_request(
                "project/add_subtitle/add_subtitle_create.yaml",
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
        except Exception as e:
            logger.error(f"create_project failed: {e}")
            return [None, {"error": "create_project_failed", "message": str(e)}]

    # 获取项目详情，常用于读取 sessionId、画幅、背景、字幕显示状态等信息。
    def get_project_detail(self, project_id, cookie=None):
        return self.run_authed_request(
            "project/add_subtitle/add_subtitle_create.yaml",
            "get_project_detail",
            cookie=cookie,
            project_id=project_id,
        )

    # 获取项目处理状态，如视频是否上传完成、媒体是否处理完成。
    def get_project_status(self, project_id, cookie=None):
        return self.run_authed_request(
            "project/add_subtitle/add_subtitle_create.yaml",
            "get_project_status",
            cookie=cookie,
            project_id=project_id,
        )

    # 获取项目媒体源信息，如视频地址、轨道信息、雪碧图地址等。
    def get_project_source(self, project_id, cookie=None):
        return self.run_authed_request(
            "project/add_subtitle/add_subtitle_create.yaml",
            "get_project_source",
            cookie=cookie,
            project_id=project_id,
        )

    # 获取项目说话人信息。
    def get_project_speaker_info(self, project_id, cookie=None):
        return self.run_authed_request(
            "project/add_subtitle/add_subtitle_create.yaml",
            "get_project_speaker_info",
            cookie=cookie,
            project_id=project_id,
        )

    # 获取项目字幕数据，包含原文轨和译文轨。
    def get_project_subtitle(self, project_id, cookie=None):
        return self.run_authed_request(
            "project/add_subtitle/add_subtitle_create.yaml",
            "get_project_subtitle",
            cookie=cookie,
            project_id=project_id,
        )

    # 获取项目字幕样式配置。
    def get_project_style(self, project_id, cookie=None):
        return self.run_authed_request(
            "project/add_subtitle/add_subtitle_create.yaml",
            "get_project_style",
            cookie=cookie,
            project_id=project_id,
        )

    # 更新项目每行字幕字数上限。
    def update_char_num(self, project_id, char_num=60, cookie=None):
        return self.run_authed_request(
            "project/add_subtitle/add_subtitle_create.yaml",
            "update_char_num",
            cookie=cookie,
            project_id=project_id,
            char_num=char_num,
        )

    # 一键执行建项目主流程：预创建、正式创建、上传视频/音频/封面并等待媒体就绪。
    def create_project_flow(self, name=None, cookie=None, video_path=None, image_path=None, audio_path=None):
        project_name = self.build_project_name(name=name, video_path=video_path)
        pre_status, pre_data = self.pre_create_project(cookie=cookie)
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
                    "created_project_id": project_id,
                    "created_temp_id": temp_id,
                    "test_project_id": project_id,
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


if __name__ == "__main__":
    ensure_test_data_dirs()
    api = ProjCreate()
    status_code, data = api.create_project_flow(f"Codex Create {int(time.time())}")
    print(status_code, data)
