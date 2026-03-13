import time

from api_moudle.base_api import BaseApi
from common.logger import logger


class ProjList(BaseApi):
    # 获取首页项目列表
    def get_proj_list(self, pageIndex=0, pageSize=12, cookie=None):
        try:
            last_response = None
            for attempt in range(1, 4):
                response = self.run_authed_request(
                    "proj_list.yaml",
                    "get_proj_list",
                    cookie=cookie,
                    pageIndex=pageIndex,
                    pageSize=pageSize,
                )
                last_response = response
                if response[0] is not None:
                    return response
                logger.warning(f"获取项目列表第 {attempt} 次失败，准备重试: {response[1]}")
                time.sleep(1)
            return last_response
        except Exception as e:
            logger.error(f"获取项目列表失败，错误: {e}")
            return [None, {"error": "get_proj_list_failed", "message": str(e)}]


if __name__ == "__main__":
    ProjList().get_proj_list()
