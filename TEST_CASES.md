# 测试用例说明

## 1. 文档范围

本文档用于说明当前 `test_case/` 目录下的自动化测试用例，主要包括：

- 测试模块执行顺序
- 各测试文件职责
- 用例之间的依赖关系
- `extract.yaml` 中的数据流转
- 推荐运行方式

## 2. 测试发现与执行规则

- 测试目录：`test_case/`
- 测试发现规则定义在 `pytest.ini`
- 默认执行的回归标记：`P0`
- 默认报告输出目录：
  - `allure-results/`
  - `reports/`

### 默认执行顺序

当前 `run.py` 和 `test_case/conftest.py` 使用相同的模块执行顺序：

1. `test_case/test_login.py`
2. `test_case/test_proj_create.py`
3. `test_case/test_home_proj_update.py`
4. `test_case/test_proj_list.py`
5. `test_case/test_timeline.py`
6. `test_case/test_proj_subtitle.py`
7. `test_case/test_space_management.py`

### 当前运行行为

- `test_case/conftest.py` 会在测试会话开始时清空一次 `extract.yaml`
- 默认只执行 `P0` 用例
- 如需执行全部用例，可增加参数 `--run-all-cases`

## 3. 公共数据流转

多个测试文件通过 `extract.yaml` 共享运行时数据。

常用字段如下：

- `code`：登录验证码
- `cookie`：登录后的鉴权 Cookie
- `created_project_id`：最近一次创建成功的项目 id
- `created_temp_id`：最近一次创建项目时的临时 id
- `test_project_id`：下游测试当前使用的项目 id
- `uploaded_video_project_id`：最近一次完成默认视频上传的项目 id
- `uploaded_image_project_id`：最近一次完成缩略图上传的项目 id
- `uploaded_audio_project_id`：最近一次完成音频上传的项目 id
- `timeline_project_id`：时间轴测试选择到的项目 id
- `subtitle_project_id`：字幕测试选择到的项目 id

当前设计说明：

- `test_proj_create.py` 是项目数据的主要生产者
- `test_home_proj_update.py` 直接复用 `test_proj_create.py` 创建出的项目
- `test_timeline.py` 和 `test_proj_subtitle.py` 会优先选择最近一个可用的项目

## 4. 各测试模块说明

### 4.1 `test_case/test_login.py`

用途：

- 验证邮箱验证码获取与登录流程

当前用例：

- `test_input_correct_email`
  - 获取登录验证码
  - 将 `code` 写入 `extract.yaml`
- `test_input_error_email`
  - 错误邮箱格式场景
  - 当前跳过
- `test_right_code_login`
  - 使用 `extract.yaml` 中的验证码登录
  - 将 `cookie` 写入 `extract.yaml`
- `test_error_code_login`
  - 错误验证码登录场景

依赖说明：

- 该模块应优先执行，供后续需要登录态的业务模块使用

### 4.2 `test_case/test_proj_create.py`

用途：

- 创建项目
- 上传默认视频、缩略图和音频
- 校验项目媒体资源就绪

当前用例：

- `test_create_project_and_upload_default_video`
  - 使用默认视频创建项目
  - 上传视频
  - 上传生成的缩略图
  - 上传生成的音频
  - 等待项目媒体资源就绪

数据写入：

- 写入 `created_project_id`
- 写入 `created_temp_id`
- 写入 `test_project_id`
- 写入上传文件相关项目 id 和 upload id

依赖说明：

- 下游项目、时间轴、字幕模块依赖这里创建出来的项目

### 4.3 `test_case/test_home_proj_update.py`

用途：

- 验证项目名称修改接口

当前用例：

- `test_update_project_name_with_valid_params`
  - 复用 `test_proj_create.py` 创建的项目
  - 正常修改项目名称
- `test_update_project_name_with_invalid_id`
  - 无效项目 id 场景
- `test_update_project_name_with_empty_name`
  - 当前跳过
- `test_update_project_name_with_long_name`
  - 当前跳过

重要说明：

- 该模块当前不会再创建新项目
- 如果单独运行且前面没有执行项目创建，会直接跳过

### 4.4 `test_case/test_proj_list.py`

用途：

- 验证项目列表接口

当前用例：

- `test_get_correct_proj_list`
- `test_proj_list_with_pagination`
- `test_proj_list_contains_required_fields`
- `test_get_proj_list_without_login`
- `test_proj_list_response_time`

特点：

- 不依赖特定项目 id
- 主要验证列表结构、权限和响应时间

### 4.5 `test_case/test_timeline.py`

用途：

- 验证时间轴视频开关功能

当前用例：

- `test_update_video_visible_toggle`
  - 选择最近一个可用的时间轴项目
  - 关闭视频显示
  - 再重新打开视频显示
  - 在 `finally` 中恢复原始状态

项目选择优先级：

1. `created_project_id`
2. `uploaded_video_project_id`
3. `timeline_project_id`
4. `test_project_id`

数据写入：

- 写入 `timeline_project_id`

### 4.6 `test_case/test_proj_subtitle.py`

用途：

- 验证字幕获取、编辑、翻译、新增、删除和显示模式切换

当前用例：

- `test_get_project_subtitle`
  - 等待原文和译文字幕列表准备完成
- `test_batch_edit_subtitle`
  - 编辑译文字幕文本
  - 最后恢复原始文本
- `test_edit_original_subtitle_and_translate`
  - 编辑原文字幕
  - 触发翻译
  - 等待翻译结果
  - 最后恢复原文和译文
- `test_add_new_subtitle_and_translate`
  - 新增一条字幕
  - 编辑新增原文
  - 触发翻译
  - 最后删除该新增字幕
- `test_update_subtitle_show`
  - 切换原文、译文、双语和关闭模式
  - 最后恢复显示模式
- `test_delete_new_subtitle`
  - 新增字幕
  - 删除字幕
  - 校验原文和译文都已消失

项目选择优先级：

1. `uploaded_video_project_id`
2. `subtitle_project_id`
3. `created_project_id`
4. `test_project_id`

数据写入：

- 写入 `subtitle_project_id`

### 4.7 `test_case/test_space_management.py`

用途：

- 验证空间管理相关列表接口

当前用例：

- `test_get_export_video_list`
- `test_get_upload_video_material_list`
- `test_get_user_clone_voice_list`
- `test_get_user_voice_list`
- `test_get_export_video_list_with_pagination`
  - 参数化为 3 条
  - 当前跳过
- `test_space_management_response_time`
- `test_space_management_with_invalid_cookie`
  - 参数化为 2 条

特点：

- 不依赖项目创建流程
- 主要验证列表数据、权限和性能

## 5. 推荐运行方式

### 按固定顺序执行默认 P0 回归

```bash
python run.py
```

### 直接使用 pytest 执行

```bash
pytest -vv -s test_case
```

说明：

- `test_case/conftest.py` 已经固定了模块顺序
- 所以 `pytest test_case` 和 `python run.py` 的模块执行顺序一致

### 执行全部用例，包括非 P0 场景

```bash
pytest -vv -s test_case --run-all-cases
```

### 只执行指定模块

```bash
pytest -vv -s test_case/test_proj_create.py test_case/test_home_proj_update.py
```

## 6. 维护建议

- `extract.yaml` 含有运行时凭证和环境数据，不建议提交到 Git
- `test_proj_create.py` 应保持在依赖它的模块之前执行
- 下游复用项目的用例尽量直接读取 `extract.yaml`，避免重复创建项目
- 修改型用例应尽量在 `finally` 中补充恢复或清理逻辑
