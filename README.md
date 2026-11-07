# CampusNotice 校园通知智能管理助手

## 一、项目简介

CampusNotice 是一个基于 Python Flask 开发的校园通知智能管理助手，旨在帮助大学生集中管理分散的校园通知、活动信息和重要时间节点，提高校园事务管理效率。

## 二、主要功能

1. **首页概览**：展示通知总数、待处理事项和近期截止事项。
2. **通知导入**：支持 PDF、Word 和 TXT 文件导入，提取通知文本并进行预览。
3. **通知管理**：支持新增、编辑、删除和搜索校园通知。
4. **截止日历**：集中展示通知中的重要时间节点，并支持切换完成状态。
5. **数据统计**：展示校园通知及待处理事项的统计信息。

## 三、技术栈

- 开发语言：Python
- Web 框架：Flask
- 前端技术：HTML、CSS、JavaScript
- 模板引擎：Jinja2
- PDF 文档解析：pypdf
- Word 文档解析：python-docx
- 版本控制：Git
- 项目托管：GitHub

## 四、项目结构

```text
CampusNotice_47/
├── app/                 # 应用程序主体
│   ├── services/        # 业务服务及文档解析
│   └── templates/       # 页面模板
├── docs/                # 项目及 Git 协作文档
├── requirements.txt     # 项目依赖
├── run.py               # 项目启动入口
├── README.md            # 项目说明
└── LICENSE              # MIT 开源许可证
```

## 五、环境配置与运行

### 1. 环境要求

- Python 3.10
- Git

### 2. 克隆项目

```bash
git clone https://github.com/Belle-k/CampusNotice_47.git
cd CampusNotice_47
```

### 3. 创建虚拟环境

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 启动项目

```bash
python run.py
```

启动后，在浏览器访问：

`http://127.0.0.1:5000`

## 六、Git 分支管理

项目采用 Git 分支协作方式：

- `main`：稳定版本分支。
- `develop`：开发集成分支。
- `feature/*`：功能开发分支。

开发过程中通过创建分支、提交代码、推送远程仓库和 Pull Request 完成功能合并，并通过实际分支冲突演示验证冲突解决流程。

## 七、参与讨论

欢迎通过 GitHub Issues 提交使用反馈、功能建议和问题。

项目讨论：[CampusNotice Issues](https://github.com/Belle-k/CampusNotice_47/issues)

## 八、开源许可

本项目采用 MIT License 开源协议。