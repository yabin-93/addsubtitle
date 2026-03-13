from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
TEST_DATA_DIR = PROJECT_ROOT / "test_data"
UPLOAD_FILES_DIR = TEST_DATA_DIR / "upload_files"
VIDEO_DIR = UPLOAD_FILES_DIR / "video"
AUDIO_DIR = UPLOAD_FILES_DIR / "audio"
IMAGE_DIR = UPLOAD_FILES_DIR / "image"
TEMP_DIR = TEST_DATA_DIR / "temp"
DEFAULT_VIDEO_FILE_NAME = "英文30S.mp4"
DEFAULT_AUDIO_FILE_NAME = "audio.mp3"
DEFAULT_IMAGE_FILE_NAME = "cover.png"


def ensure_test_data_dirs():
    for path in (TEST_DATA_DIR, UPLOAD_FILES_DIR, VIDEO_DIR, AUDIO_DIR, IMAGE_DIR, TEMP_DIR):
        path.mkdir(parents=True, exist_ok=True)


def get_upload_file_path(category, filename):
    mapping = {
        "video": VIDEO_DIR,
        "audio": AUDIO_DIR,
        "image": IMAGE_DIR,
        "temp": TEMP_DIR,
    }
    if category not in mapping:
        raise ValueError(f"Unsupported category: {category}")
    return mapping[category] / filename


def get_default_video_path():
    return get_upload_file_path("video", DEFAULT_VIDEO_FILE_NAME)


def get_default_audio_path():
    return get_upload_file_path("audio", DEFAULT_AUDIO_FILE_NAME)


def get_default_image_path():
    return get_upload_file_path("image", DEFAULT_IMAGE_FILE_NAME)


def require_upload_file(category, filename):
    file_path = get_upload_file_path(category, filename)
    if not file_path.exists():
        raise FileNotFoundError(f"Upload file not found: {file_path}")
    return file_path
