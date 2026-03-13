import os
import time

import pytest


REGRESSION_MARK_EXPRESSION = "P0"
ORDERED_TEST_FILES = [
    "test_case/auth/test_login.py",
    "test_case/project/add_subtitle/test_add_subtitle_create.py",
    "test_case/project/home/test_proj_name_update.py",
    "test_case/project/home/test_proj_list.py",
    "test_case/project/add_subtitle/test_add_subtitle_timeline.py",
    "test_case/project/add_subtitle/test_add_subtitle_subtitle.py",
    "test_case/project/space/test_space_management.py",
]


if __name__ == "__main__":
    pytest.main(["-m", REGRESSION_MARK_EXPRESSION, *ORDERED_TEST_FILES])
    time.sleep(3)
    os.system("allure generate ./allure-results -o ./reports --clean")
