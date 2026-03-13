# 测试用例说明

## 1. 文档范围

本文档说明当前项目的测试目录结构、默认执行顺序、各模块职责以及 `extract.yaml` 的数据流转关系。

## 2. 目录结构

### 2.1 接口 YAML

- `api_yaml/auth/login.yaml`
- `api_yaml/project/home/proj_name_update.yaml`
- `api_yaml/project/home/proj_list.yaml`
- `api_yaml/project/add_subtitle/add_subtitle_create.yaml`
- `api_yaml/project/add_subtitle/add_subtitle_subtitle.yaml`
- `api_yaml/project/add_subtitle/add_subtitle_timeline.yaml`
- `api_yaml/project/space/space_management.yaml`

### 2.2 测试用例

- `test_case/auth/test_login.py`
- `test_case/project/home/test_proj_name_update.py`
- `test_case/project/home/test_proj_list.py`
- `test_case/project/add_subtitle/test_add_subtitle_create.py`
- `test_case/project/add_subtitle/test_add_subtitle_timeline.py`
- `test_case/project/add_subtitle/test_add_subtitle_subtitle.py`
- `test_case/project/space/test_space_management.py`

## 3. 默认执行顺序

当前 `run.py` 和 `test_case/conftest.py` 使用相同的模块顺序：

1. `test_case/auth/test_login.py`
2. `test_case/project/add_subtitle/test_add_subtitle_create.py`
3. `test_case/project/home/test_proj_name_update.py`
4. `test_case/project/home/test_proj_list.py`
5. `test_case/project/add_subtitle/test_add_subtitle_timeline.py`
6. `test_case/project/add_subtitle/test_add_subtitle_subtitle.py`
7. `test_case/project/space/test_space_management.py`

说明：

- 默认只执行 `P0` 用例
- 如需执行全部用例，可增加参数 `--run-all-cases`
- 测试会话开始时会清空一次 `extract.yaml`

## 4. 公共数据流转

多个模块通过 `extract.yaml` 共享运行时数据，常用字段如下：

- `code`：登录验证码
- `cookie`：登录后的 Cookie
- `created_project_id`：最近一次创建成功的项目 ID
- `created_temp_id`：最近一次创建项目时的临时 ID
- `test_project_id`：当前回归链路统一复用的项目 ID
- `uploaded_video_project_id`：最近一次完成视频上传的项目 ID
- `uploaded_image_project_id`：最近一次完成缩略图上传的项目 ID
- `uploaded_audio_project_id`：最近一次完成音频上传的项目 ID
- `timeline_project_id`：时间轴用例命中的项目 ID
- `subtitle_project_id`：字幕用例命中的项目 ID

## 5. 各测试模块职责

### 5.1 `test_case/auth/test_login.py`

用途：

- 获取验证码
- 使用验证码登录
- 校验错误验证码场景

### 5.2 `test_case/project/add_subtitle/test_add_subtitle_create.py`

用途：

- 创建项目
- 上传默认视频、缩略图、音频
- 等待媒体资源就绪

说明：

- 这是下游项目类测试的数据入口
- 成功后会写入 `created_project_id` 和 `test_project_id`

### 5.3 `test_case/project/home/test_proj_name_update.py`

用途：

- 修改项目名称

说明：

- 不再单独创建项目
- 直接复用 `test_add_subtitle_create.py` 创建出的项目

### 5.4 `test_case/project/home/test_proj_list.py`

用途：

- 获取项目列表
- 校验分页、字段、响应时间、未登录场景

### 5.5 `test_case/project/add_subtitle/test_add_subtitle_timeline.py`

用途：

- 校验视频轨开关

说明：

- 优先复用最近创建且可用的项目
- 会写入 `timeline_project_id`

### 5.6 `test_case/project/add_subtitle/test_add_subtitle_subtitle.py`

用途：

- 获取字幕
- 编辑译文字幕
- 编辑原文后触发翻译
- 新增字幕后翻译
- 删除字幕
- 切换字幕显示模式

说明：

- 优先复用最近一个可用字幕项目
- 会写入 `subtitle_project_id`

### 5.7 `test_case/project/space/test_space_management.py`

用途：

- 获取导出视频列表
- 获取上传素材列表
- 获取用户语音列表
- 校验无效 Cookie 场景
- 校验接口响应时间

## 6. 推荐运行方式

### 6.1 按默认顺序执行 P0 回归

```bash
python run.py
```

### 6.2 直接使用 pytest

```bash
pytest -vv -s test_case
```

### 6.3 执行全部用例

```bash
pytest -vv -s test_case --run-all-cases
```

### 6.4 执行指定模块

```bash
pytest -vv -s test_case/project/add_subtitle/test_add_subtitle_create.py test_case/project/home/test_proj_name_update.py
```

## 7. 维护建议

- `extract.yaml` 包含运行态凭证，不建议提交到 Git
- 依赖项目数据的模块要保持在 `test_add_subtitle_create.py` 之后执行
- 修改型用例尽量在 `finally` 中补充恢复或清理逻辑
- 如果继续扩展目录分层，优先保持接口模块、YAML、测试目录三者结构一致
