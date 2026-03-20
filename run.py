import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pytest

from common.send_dingding_message import SendReportMessage
from common.settings import ADD_SUBTITLE_BASE_URL


REGRESSION_MARK_EXPRESSION = "P0"
ORDERED_TEST_FILES = [
    "test_case/auth/test_login.py",
    "test_case/project/add_subtitle/test_add_subtitle_create.py",
    "test_case/project/add_subtitle/test_add_subtitle_subtitle.py",
    "test_case/project/add_subtitle/test_add_subtitle_timeline.py",
    "test_case/project/home/test_proj_list.py",
    "test_case/project/home/test_proj_name_update.py",
    "test_case/project/space/test_space_management.py",
    "test_case/project/add_subtitle/test_add_subtitle_export.py",
]
ALLURE_SUMMARY_PATH = Path("reports/widgets/summary.json")


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
        return False

    result = subprocess.run(
        [resolved_allure_bin, "generate", "./allure-results", "-o", "./reports", "--clean"],
        check=False,
    )
    return result.returncode == 0


def _load_allure_summary():
    if not ALLURE_SUMMARY_PATH.exists():
        return None

    with open(ALLURE_SUMMARY_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def _format_duration(duration_ms):
    total_seconds = max(int(duration_ms or 0) // 1000, 0)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    if minutes:
        return f"{minutes}m {seconds}s"
    return f"{seconds}s"


def _format_timestamp(timestamp_ms):
    if not timestamp_ms:
        return "-"
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")


def _build_report_message(exit_code, report_generated):
    summary = _load_allure_summary() if report_generated else None
    summary = summary or {}
    stats = summary.get("statistic", {})
    time_info = summary.get("time", {})

    failed = stats.get("failed", 0)
    broken = stats.get("broken", 0)
    skipped = stats.get("skipped", 0)
    passed = stats.get("passed", 0)
    total = stats.get("total", 0)

    if exit_code == 0 and failed == 0 and broken == 0:
        status_text = "SUCCESS"
    else:
        status_text = "FAILED"

    run_scope = "ALL" if _is_truthy(os.getenv("RUN_ALL_CASES")) else os.getenv("PYTEST_MARK_EXPRESSION", REGRESSION_MARK_EXPRESSION)

    lines = [
        "AddSubtitle 自动化测试结果",
        f"状态: {status_text}",
        f"环境: {ADD_SUBTITLE_BASE_URL}",
        f"范围: {run_scope}",
        f"总数: {total}",
        f"通过: {passed}",
        f"失败: {failed}",
        f"异常: {broken}",
        f"跳过: {skipped}",
        f"耗时: {_format_duration(time_info.get('duration', 0))}",
        f"开始时间: {_format_timestamp(time_info.get('start'))}",
        f"结束时间: {_format_timestamp(time_info.get('stop'))}",
        f"报告目录: {Path('reports').resolve() if report_generated else '未生成'}",
    ]
    return "\n".join(lines)


def _send_dingtalk_report(exit_code, report_generated):
    try:
        message = _build_report_message(exit_code, report_generated)
        SendReportMessage.send_dingtalk_message(message)
    except Exception as exc:
        print(f"Failed to send DingTalk message: {exc}")


if __name__ == "__main__":
    exit_code = pytest.main(_build_pytest_args())
    report_generated = _generate_allure_report()
    _send_dingtalk_report(exit_code, report_generated)
    sys.exit(exit_code)
