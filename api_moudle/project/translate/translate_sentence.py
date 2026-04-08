import time

from api_moudle.project.home.base_api import BaseApi


class TranslateSentence(BaseApi):
    YAML_PATH = "project/translate/translate_sentence.yaml"

    def get_project_sentence_list(self, project_id, cookie=None):
        return self.run_authed_request(
            self.YAML_PATH,
            "get_project_sentence_list",
            cookie=cookie,
            project_id=project_id,
        )

    def wait_for_project_sentence_ready(self, project_id, cookie=None, timeout=120, interval=3):
        deadline = time.time() + timeout
        latest_response = None

        while time.time() < deadline:
            status_code, data = self.get_project_sentence_list(project_id, cookie=cookie)
            latest_response = {"status_code": status_code, "data": data}

            if (
                status_code == 200
                and isinstance(data, dict)
                and data.get("success") is True
                and isinstance(data.get("data", {}).get("oriList"), list)
                and len(data.get("data", {}).get("oriList", [])) > 0
            ):
                return [200, data]

            time.sleep(interval)

        return [408, {"stage": "wait_for_project_sentence_ready", "latest": latest_response}]

