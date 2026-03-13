from api_moudle.project.home.base_api import BaseApi


class SpaceManagement(BaseApi):
    def __init__(self):
        super().__init__()
        self.yaml_path = "project/space/space_management.yaml"

    def get_export_video_list(self, cookie=None, pageIndex=0, pageSize=12, type=3):
        return self.run_authed_request(
            self.yaml_path,
            "get_export_video_list",
            cookie=cookie,
            pageIndex=pageIndex,
            pageSize=pageSize,
            type=type,
        )

    def get_upload_video_material_list(self, cookie=None, pageIndex=0, pageSize=12, type=2):
        return self.run_authed_request(
            self.yaml_path,
            "get_upload_video_material_list",
            cookie=cookie,
            pageIndex=pageIndex,
            pageSize=pageSize,
            type=type,
        )

    def get_user_clone_voice_list(self, cookie=None, pageIndex=0, pageSize=12):
        return self.run_authed_request(
            self.yaml_path,
            "get_user_clone_voice_list",
            cookie=cookie,
            pageIndex=pageIndex,
            pageSize=pageSize,
        )

    def get_user_voice_list(self, cookie=None, pageIndex=0, pageSize=12):
        return self.run_authed_request(
            self.yaml_path,
            "get_user_voice_list",
            cookie=cookie,
            pageIndex=pageIndex,
            pageSize=pageSize,
        )


if __name__ == "__main__":
    manager = SpaceManagement()
    print(manager.get_export_video_list())
    print(manager.get_upload_video_material_list())
    print(manager.get_user_clone_voice_list())
    print(manager.get_user_voice_list())
