# from string import Template
#
# import yaml
#
#
# def run_request(yaml_path, api_name, **kwargs):
#     with open(yaml_path, "r", encoding="utf-8") as f:
#         yaml_data = yaml.safe_load(f)
#         yaml_data = yaml_data[api_name]
#         # print(yaml_data)
#
#     # 替换模版，把$开头的替换成kwargs的值里面的值
#     if kwargs:
#         try:
#             yaml_data = yaml.dump(yaml_data)  # 转成字符串
#             print(yaml_data)
#             for k, v in kwargs.items():
#                 print(k, v)
#                 if isinstance(v, str):
#                     kwargs[k] = f"'{v}'"
#             yaml_data = Template(yaml_data).substitute(kwargs)
#             print(yaml_data)
#             yaml_data = yaml.safe_load(yaml_data)
#
#
#         except Exception as e:
#
#             raise
#
#
# if __name__ == '__main__':
#     yaml_path = r"E:\proj\pythonProject\addSubtitle\api_yaml\auth\login.yaml"
#     api_name = "acc_pwd_login"
#     run_request(yaml_path,api_name,code="123456")
