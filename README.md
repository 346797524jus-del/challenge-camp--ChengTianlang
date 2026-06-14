# 挑战杯麒麟赛题 · 14 天选拔集训

## 一、环境清单

- **操作系统**: Windows 11 / 银河麒麟高级服务器操作系统 (拓展阶段)
- **开发工具**: VS Code
- **AI 辅助工具**: VS Code 内置 AI 编程助手
- **运行环境**: Python 3.10+

---

## 二、项目目录结构

```
e:\挑战杯\
├── README.md                     # 本文件
├── .gitignore
│
├── phase1-basics/                # 【Phase 1】基础阶段 - 数据清洗与 Git 练习
│   ├── clean_basic.py            # 数据清洗脚本
│   ├── cleaned_dirty.csv         # 清洗后数据
│   ├── merge_day2.py             # 数据合并脚本
│   ├── merge_log.txt             # 合并日志
│   └── merged_d2.jsonl           # 合并后数据
│
├── phase2-consolidata/           # 【Phase 2】巩固阶段 - Pipeline 架构初探
│   ├── pipeline/                 # 数据处理流水线
│   ├── requirements.txt
│   ├── chat_logs.json            # 对话日志
│   ├── knowledge.json            # 知识库
│   ├── preferences.json          # 偏好设置
│   ├── tool_results.json         # 工具调用结果
│   ├── git_notes.md              # Git 学习笔记
│   └── report.md                 # 阶段报告
│
└── phase3-advance/               # 【Phase 3】进阶阶段 - 「小石头」智能助手
    ├── README.md                 # Phase3 详细说明
    ├── .env.example              # 环境变量模板（不含密钥）
    │
    ├── backend/                  # 后端 - FastAPI 四层架构
    │   ├── main.py               # 应用入口
    │   ├── start.bat             # Windows 启动脚本
    │   ├── requirements.txt      # Python 依赖
    │   ├── docker-compose.yml    # Docker 编排（Milvus + MySQL）
    │   ├── .env.example          # 环境变量模板
    │   ├── diagnose.py           # 诊断脚本
    │   ├── app/
    │   │   ├── config.py         # 集中配置（环境变量读取）
    │   │   ├── database.py       # 数据库引擎（MySQL/SQLite 自动回退）
    │   │   ├── file_processor.py # 文件生成（Word/Excel/PPT）+ 解析
    │   │   ├── api/
    │   │   │   └── routes.py     # FastAPI 路由（Chat/File/Search/Knowledge）
    │   │   ├── models/           # SQLAlchemy 数据模型
    │   │   │   ├── session.py    # 会话
    │   │   │   ├── message.py    # 消息
    │   │   │   ├── preference.py # 用户偏好
    │   │   │   ├── knowledge.py  # 知识条目
    │   │   │   └── file_record.py# 文件记录
    │   │   ├── pipeline/         # 四层处理管线
    │   │   │   ├── pipeline.py   # 主管线调度（同步 + 流式）
    │   │   │   ├── input_layer.py    # Layer 1: 意图理解 + 指代消解
    │   │   │   ├── data_layer.py     # Layer 2: 数据获取（联网搜索 + RAG + 记忆）
    │   │   │   ├── process_layer.py  # Layer 3: LLM 数据处理清洗
    │   │   │   ├── output_layer.py   # Layer 4: 结构化输出呈现
    │   │   │   ├── style_engine.py   # 样式引擎
    │   │   │   └── guided_mode.py    # 需求引导模式
    │   │   ├── rag/              # RAG 向量检索
    │   │   │   ├── vector_db_manager.py  # Milvus/ChromaDB 管理
    │   │   │   ├── vector_retriever.py   # 向量检索 + 重排序
    │   │   │   └── document_loader.py    # 文档加载器
    │   │   └── mcp/              # MCP 协议集成
    │   │       ├── mcp_manager.py
    │   │       └── servers_config.json
    │   ├── mcp/
    │   │   └── servers_config.json
    │   ├── test_chat.py          # 聊天接口测试
    │   └── test_sse.py           # SSE 流式测试
    │
    └── frontend/                 # 前端 - React + Vite
        ├── index.html
        ├── package.json
        ├── vite.config.js
        ├── tailwind.config.js
        ├── public/
        └── src/
            ├── App.jsx           # 主组件
            ├── main.jsx          # 入口
            ├── api/index.js      # API 封装
            └── styles.css        # 全局样式
```

---

## 三、Phase 各阶段说明

### Phase 1 — 基础阶段
- 数据清洗（缺失值处理、去重、格式化）
- JSONL 数据合并
- Git 版本控制基础

### Phase 2 — 巩固阶段
- Pipeline 数据处理流水线设计
- 知识库构建（JSON 存储）
- 对话日志与偏好记录
- Git 分支管理与协作

### Phase 3 — 进阶阶段（「小石头」智能助手）
> **技术栈**: FastAPI + React + DeepSeek LLM + SQLite/MySQL + ChromaDB/Milvus

**四层架构**：
| 层级 | 名称 | 职责 |
|------|------|------|
| Layer 1 | 输入理解层 | 意图识别、指代消解、实体提取 |
| Layer 2 | 数据获取层 | 联网搜索（DuckDuckGo/Bing）、RAG 知识库、会话记忆 |
| Layer 3 | 数据处理层 | LLM 清洗、结构化、格式规范 |
| Layer 4 | 输出呈现层 | Markdown 格式化、风格适配 |

**核心功能**：
- 🤖 **多轮对话**: 上下文记忆 + 任务状态持久化，支持指代消解和格式转换指令
- 📄 **文件生成**: Word/Excel/PPT（WPS三件套），支持 6 阶段进度展示
- 🔍 **联网搜索**: 实时信息查询（天气、比分、新闻等），多源搜索结果
- 📚 **RAG 知识库**: 向量检索增强生成
- 📡 **MCP 协议**: 工具集成（天气/文件/地图）
- 🌐 **需求引导**: 逐步确认生成需求
- 🎨 **个性化**: 自定义主题、昵称、头像

---

## 四、快速启动（Phase 3）

### 后端
```bash
cd phase3-advance/backend
pip install -r requirements.txt
# 复制 .env.example 为 .env 并填入 API Key
python main.py
# 服务启动在 http://localhost:8081
# API 文档: http://localhost:8081/docs
```

### 前端
```bash
cd phase3-advance/frontend
npm install
npm run dev
# 开发服务器: http://localhost:3000
```

### 环境变量 (.env)
```env
AI_API_KEY=sk-xxx               # DeepSeek API Key
AI_API_BASE_URL=https://api.deepseek.com/v1
AI_MODEL_NAME=deepseek-chat
MYSQL_HOST=localhost             # MySQL（可选，自动回退 SQLite）
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DATABASE=agent_memory
MILVUS_HOST=localhost            # Milvus（可选，自动回退 ChromaDB）
MILVUS_PORT=19530
```

---

## 五、依赖清单

### 后端 (Python)
```
fastapi, uvicorn, pydantic-settings, sqlalchemy, pymysql
openai, sse-starlette, httpx, loguru
python-docx, openpyxl, python-pptx, pandas
pymilvus, chromadb, duckduckgo-search, beautifulsoup4
langchain, tenacity, redis, aiofiles
```

### 前端 (Node.js)
```
react, react-dom, react-markdown, remark-gfm
lucide-react, @vitejs/plugin-react, tailwindcss