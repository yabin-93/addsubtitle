from api_moudle.project.home.base_api import BaseApi
from common.logger import logger


class ProjUpdate(BaseApi):
    def update_project_name(self, project_id, name, cookie=None):
        try:
            return self.run_authed_request(
                "project/home/proj_name_update.yaml",
                "update_project_name",
                cookie=cookie,
                project_id=project_id,
                name=name,
            )
        except Exception as e:
            logger.error(f"修改项目名称失败，错误: {e}")
            return [None, {"error": "update_project_name_failed", "message": str(e)}]


if __name__ == "__main__":
    from api_moudle.project.home.proj_list import ProjList

    status_code, data = ProjList().get_proj_list()
    if status_code == 200 and data["data"]["rows"]:
        project_id = data["data"]["rows"][0]["id"]
        print(ProjUpdate().update_project_name(project_id, "新项目名称"))
    else:
        print(status_code, data)
