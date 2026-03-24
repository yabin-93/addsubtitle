import json as json_lib
import os
from pathlib import Path
from string import Template

import requests
import urllib3
import yaml

from common.auth_util import get_cookie
from common.logger import logger
from common.settings import ADD_SUBTITLE_BASE_URL

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BaseApi:
    def __init__(self):
        self.request = requests.session()
        self.request.verify = False

    # 发送底层 HTTP 请求，统一处理请求头、表单上传、日志和异常。
    def request_api(self, method, api, params=None, data=None, json=None, headers=None, multipart_form=None):
        host = ADD_SUBTITLE_BASE_URL
        url_api = host + api

        logger.info(f"Start request: {method.upper()} {url_api}")
        logger.debug(
            f"Request args: params={params}, data={data}, json={json}, headers={headers}, multipart_form={multipart_form}"
        )

        try:
            if headers and headers.get("Cookie"):
                self.request.cookies.clear()

            request_headers = dict(headers) if headers else None
            if method == "post":
                if multipart_form is not None:
                    if request_headers:
                        request_headers = {
                            key: value
                            for key, value in request_headers.items()
                            if key.lower() != "content-type"
                        }
                    files = []
                    for key, value in multipart_form.items():
                        if value is None:
                            continue
                        if isinstance(value, (dict, list)):
                            normalized_value = json_lib.dumps(value, ensure_ascii=False)
                        elif isinstance(value, bool):
                            normalized_value = "true" if value else "false"
                        else:
                            normalized_value = str(value)
                        files.append((key, (None, normalized_value)))
                    res = self.request.post(url_api, files=files, headers=request_headers)
                else:
                    res = self.request.post(url_api, json=json, data=data, headers=request_headers)
            else:
                res = self.request.get(url_api, params=params, headers=request_headers)

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

    # 发送需要登录态的请求；如果默认 cookie 失效，则自动刷新后重试一次。
    def run_authed_request(self, yaml_path, api_name, cookie=None, **kwargs):
        provided_cookie = cookie is not None
        active_cookie = cookie or get_cookie()
        resp = self.run_request(yaml_path, api_name, cookie=active_cookie, **kwargs)

        if not provided_cookie and resp and resp[0] == 401:
            logger.info(f"Cookie expired, refresh and retry: {api_name}")
            active_cookie = get_cookie(force_refresh=True)
            resp = self.run_request(yaml_path, api_name, cookie=active_cookie, **kwargs)

        return resp

    # 从 YAML 中加载接口定义并替换参数，最后交给 request_api 执行。
    def run_request(self, yaml_path, api_name, **kwargs):
        project_root = Path(__file__).resolve().parents[3]
        project_path = str(project_root / "api_yaml" / yaml_path)
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
                multipart_mode = "multipart_form:" in yaml_data
                for k, v in kwargs.items():
                    if multipart_mode:
                        kwargs[k] = json_lib.dumps(v, ensure_ascii=False)
                    elif isinstance(v, str):
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
    BaseApi().run_request("auth/login.yaml", "get_code")
