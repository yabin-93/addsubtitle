import os
from string import Template

import requests
import yaml

from common.auth_util import get_cookie
from common.logger import logger


class BaseApi:
    def __init__(self):
        self.request = requests.session()

    def request_api(self, method, api, params=None, data=None, json=None, headers=None):
        host = "https://staging.addsubtitle.ai"
        url_api = host + api

        logger.info(f"Start request: {method.upper()} {url_api}")
        logger.debug(f"Request args: params={params}, data={data}, json={json}, headers={headers}")

        try:
            if headers and headers.get("Cookie"):
                self.request.cookies.clear()

            if method == "post":
                res = self.request.post(url_api, json=json, data=data, headers=headers)
            else:
                res = self.request.get(url_api, params=params, headers=headers)

            status_code = res.status_code
            logger.info(f"Request done: {method.upper()} {url_api} - Status Code: {status_code}")

            try:
                res = res.json()
                logger.debug(f"Response json: {res}")
            except Exception:
                res = res.text
                logger.debug(f"Response text: {res}")

            return [status_code, res]
        except requests.RequestException as e:
            logger.error(f"Network request failed: {method} {url_api} - {e}")
            return [None, {"error": "network_request_failed", "message": str(e)}]
        except Exception as e:
            logger.error(f"Request handling failed: {method} {url_api} - {e}")
            return [None, {"error": "request_handle_failed", "message": str(e)}]

    def run_authed_request(self, yaml_path, api_name, cookie=None, **kwargs):
        provided_cookie = cookie is not None
        active_cookie = cookie or get_cookie()
        resp = self.run_request(yaml_path, api_name, cookie=active_cookie, **kwargs)

        if not provided_cookie and resp and resp[0] == 401:
            logger.info(f"Cookie expired, refresh and retry: {api_name}")
            active_cookie = get_cookie(force_refresh=True)
            resp = self.run_request(yaml_path, api_name, cookie=active_cookie, **kwargs)

        return resp

    def run_request(self, yaml_path, api_name, **kwargs):
        project_path = os.path.dirname(os.path.dirname(__file__)) + "/api_yaml/" + yaml_path
        logger.info(f"Load YAML config: {project_path}, api_name: {api_name}")
        logger.debug(f"Runtime args: {kwargs}")

        try:
            with open(project_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)[api_name]
                logger.debug(f"YAML config: {yaml_data}")
        except Exception as e:
            logger.error(f"Read YAML failed: {project_path} - {e}")
            raise

        if kwargs:
            try:
                yaml_data = yaml.dump(yaml_data)
                for k, v in kwargs.items():
                    if isinstance(v, str):
                        kwargs[k] = f"'{v}'"
                yaml_data = Template(yaml_data).substitute(kwargs)
                yaml_data = yaml.safe_load(yaml_data)
                logger.debug(f"Resolved request config: {yaml_data}")
            except Exception as e:
                logger.error(f"Template substitution failed: {e}")
                raise

        res = self.request_api(**yaml_data)
        logger.info(f"Request finished, status code: {res[0] if res else 'None'}")
        logger.info("==" * 60)

        return res


if __name__ == "__main__":
    BaseApi().run_request("login.yaml", "get_code")
