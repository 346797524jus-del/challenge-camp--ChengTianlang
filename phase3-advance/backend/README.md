# P3 Agent System - Backend

四层架构智能体系统（Python/FastAPI 重构版）

## 架构概览

```
用户输入
   ↓
┌──────────────────────────────────────┐
│  Layer 1: Input Understanding Layer  │  ← app/pipeline/input_layer.py
│  意图分析 · 实体提取 · 任务分解        │
├──────────────────────────────────────┤
│  Layer 2: Data Acquisition Layer     │  ← app/pipeline/data_layer.py
│  知识库 → 记忆库 → 网络搜索 → 文件     │
├──────────────────────────────────────┤
│  Layer 3: Data Processing Layer      │  ← app/pipeline/process_layer.py
│  LLM 清洗 · 去重 · 整合 · 结构化       │
├──────────────────────────────────────┤
│  Layer 4: Output Presentation Layer  │  ← app/pipeline/output_layer.py
│  个性化调整 · 风格润色 · 安全过滤       │
└──────────────────────────────────────┘
   ↓
最终回复 (流式 SSE)
```

## 项目结构

```
backend/
├── main.py                    # FastAPI 入口
├── start.bat                  # Windows 启动脚本
├── requirements.txt           # Python 依赖
├── .env.example               # 环境变量模板
├── app/
│   ├── config.py              # 配置管理（环境变量读取）
│   ├── database.py            # SQLAlchemy 引擎 & 会话
│   ├── file_processor.py      # 文件处理（PDF/Word/Excel/CSV/TXT/图片）
│   ├── pipeline/              # 四层流水线
│   │   ├── __init__.py
│   │   ├── input_layer.py     # Layer 1: 输入理解
│   │   ├── data_layer.py      # Layer 2: 数据获取
│   │   ├── process_layer.py   # Layer 3: 数据处理
│   │   ├── output_layer.py    # Layer 4: 输出呈现
│   │   └── pipeline.py        # 总调度器
│   ├── models/                # SQLAlchemy ORM 模型
│   │   ├── __init__.py
│   │   ├── session.py         # 会话模型
│   │   ├── message.py         # 消息模型
│   │   ├── preference.py      # 用户偏好模型
│   │   ├── knowledge.py       # 知识库模型
│   │   └── file_record.py     # 文件记录模型
│   └── api/
│       ├── __init__.py
│       └── routes.py          # 所有 API 路由
├── uploads/                   # 上传文件目录
├── generated-docs/            # 生成文档目录
└── logs/                      # 日志目录
```

## 快速启动

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的 AI_API_KEY
```

### 2. 启动后端

```bash
# Windows
start.bat

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 3. 访问

- API Docs: http://localhost:8081/docs
- Health Check: http://localhost:8081/api/health

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/sessions | 会话列表 |
| POST | /api/sessions | 创建会话 |
| PUT | /api/sessions/{id}/rename | 重命名会话 |
| PUT | /api/sessions/{id}/style | 修改头像昵称 |
| DELETE | /api/sessions/{id} | 删除会话 |
| POST | /api/chat/stream | 流式聊天（SSE） |
| POST | /api/chat | 同步聊天 |
| POST | /api/files/upload | 上传文件 |
| GET | /api/files/{session_id} | 文件列表 |
| POST | /api/files/clean | 数据清洗 |
| POST | /api/search | 搜索 |
| POST | /api/feedback | 点赞/拉踩 |
| GET/PUT | /api/preferences | 偏好管理 |
| POST | /api/documents/generate/* | 生成文档 |
| POST | /api/sessions/{id}/branch | 创建分支 |

## 测试用例验证

1. ✅ 创建新对话 → 出现在历史列表 → 可重命名/删除
2. ✅ 上传Excel → "清洗重复数据并生成总结" → 生成清洗后文件
3. ✅ 开启深度思考 → "制作介绍AI的PPT" → 展示思考过程
4. ✅ 搜索"今天天气" → 优先知识库 → 无结果则联网
5. ✅ 点赞/拉踩 → 记忆库更新偏好
6. ✅ 修改头像昵称 → 界面即时更新
7. ✅ 流式输出，回复速度可感知