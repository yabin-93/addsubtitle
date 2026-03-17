import os
import shutil
import subprocess
import sys

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


def _is_truthy(value):
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _build_pytest_args():
    args = []

    if _is_truthy(os.getenv("RUN_ALL_CASES")):
        args.append("--run-all-cases")
    else:
        args.extend(["-m", os.getenv("PYTEST_MARK_EXPRESSION", REGRESSION_MARK_EXPRESSION)])

    junit_xml_path = os.getenv("JUNIT_XML_PATH")
    if junit_xml_path:
        args.extend(["--junitxml", junit_xml_path])

    args.extend(ORDERED_TEST_FILES)
    return args


def _generate_allure_report():
    allure_bin = os.getenv("ALLURE_BIN", "allure")
    resolved_allure_bin = shutil.which(allure_bin)
    if resolved_allure_bin is None:
        print(f"Skip Allure report generation because '{allure_bin}' is not available in PATH.")
        return

    subprocess.run(
        [resolved_allure_bin, "generate", "./allure-results", "-o", "./reports", "--clean"],
        check=False,
    )


if __name__ == "__main__":
    exit_code = pytest.main(_build_pytest_args())
    _generate_allure_report()
    sys.exit(exit_code)
