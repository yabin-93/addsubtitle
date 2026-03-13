from pathlib import Path

import yaml


EXTRACT_YAML_PATH = Path(__file__).resolve().parent.parent / "extract.yaml"
_MISSING = object()


def _load_yaml():
    try:
        with open(EXTRACT_YAML_PATH, "r", encoding="utf-8") as file:
            config = yaml.load(file, Loader=yaml.FullLoader)
    except FileNotFoundError:
        return {}
    return config or {}


def read_yaml(key, default=_MISSING):
    config = _load_yaml()
    if key in config:
        return config[key]
    if default is not _MISSING:
        return default
    raise KeyError(f"{key} not found in {EXTRACT_YAML_PATH}")


def write_yaml(data):
    config = _load_yaml()
    config.update(data)
    with open(EXTRACT_YAML_PATH, "w", encoding="utf-8") as file:
        yaml.safe_dump(config, stream=file, allow_unicode=True, sort_keys=False)


def clear_yaml():
    with open(EXTRACT_YAML_PATH, "w", encoding="utf-8") as file:
        yaml.safe_dump({}, stream=file, allow_unicode=True, sort_keys=False)
