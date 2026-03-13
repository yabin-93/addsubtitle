from pathlib import Path

import pytest

from common.yaml_util import clear_yaml


REGRESSION_MARK = "P0"
ORDERED_TEST_FILES = [
    "test_case/test_login.py",
    "test_case/test_proj_create.py",
    "test_case/test_home_proj_update.py",
    "test_case/test_proj_list.py",
    "test_case/test_timeline.py",
    "test_case/test_proj_subtitle.py",
    "test_case/test_space_management.py",
]
ORDERED_TEST_FILE_INDEX = {path: index for index, path in enumerate(ORDERED_TEST_FILES)}
NON_REGRESSION_SKIP_REASON = "非上线前回归用例，暂时跳过"


def pytest_addoption(parser):
    parser.addoption(
        "--run-all-cases",
        action="store_true",
        default=False,
        help="运行全部用例，包含非上线前回归用例",
    )


def pytest_collection_modifyitems(config, items):
    def sort_key(item):
        item_path = Path(str(item.fspath)).as_posix()
        relative_path = f"test_case/{Path(item_path).name}"
        return (
            ORDERED_TEST_FILE_INDEX.get(relative_path, len(ORDERED_TEST_FILE_INDEX)),
            item_path,
            item.name,
        )

    items.sort(key=sort_key)

    if config.getoption("--run-all-cases"):
        return

    for item in items:
        item_path = Path(str(item.fspath)).as_posix()
        if "/test_case/" not in f"/{item_path}":
            continue
        if item.get_closest_marker(REGRESSION_MARK):
            continue
        item.add_marker(pytest.mark.skip(reason=NON_REGRESSION_SKIP_REASON))


@pytest.fixture(scope="session", autouse=True)
def exe_assert():
    clear_yaml()
