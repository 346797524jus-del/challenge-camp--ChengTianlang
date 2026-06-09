# 🤖 AI 编程小助手 - 智能体雏形项目

> 基于 LangChain4j + DeepSeek 的 AI 智能体（Agent）项目，能够生成 WPS 文档并在线预览

[![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.5.3-brightgreen.svg)](https://spring.io/projects/spring-boot)
[![Vue.js](https://img.shields.io/badge/Vue.js-3.4.0-4FC08D.svg)](https://vuejs.org/)
[![LangChain4j](https://img.shields.io/badge/LangChain4j-1.1.0-blue.svg)](https://github.com/langchain4j/langchain4j)
[![Java](https://img.shields.io/badge/Java-21-orange.svg)](https://www.oracle.com/java/)

## ✨ 项目亮点

本项目是一个 **AI 智能体（Agent）雏形**，采用 ReAct（思考-行动-观察）模式，让 AI 能够：

1. **理解用户需求** - 分析用户想要什么类型的文档
2. **自主调用工具** - 选择合适的工具生成文档
3. **生成 WPS 文件** - 支持 Word、Excel、PPT 三种格式
4. **在线预览下载** - 生成的文件可直接在网页端预览和下载

### 🎯 核心功能

| 功能 | 说明 | 工具 |
|------|------|------|
| 📄 **生成 Word 文档** | 简历、报告、学习笔记等 | `generateWordDocument` / `generateResume` |
| 📊 **生成 Excel 表格** | 数据统计、学习计划等 | `generateExcelSpreadsheet` / `generateStudyPlan` |
| 📽️ **生成 PPT 演示文稿** | 项目汇报、知识分享等 | `generatePresentation` |
| 🔍 **搜索面试题** | 实时获取最新面试题目 | `interviewQuestionSearch` |
| 📁 **文件管理** | 在线预览、下载、删除生成的文件 | `FileManager` 面板 |

### 🏗️ 技术架构

```
┌─────────────────────────────────────┐
│          Vue.js 3 前端               │
│  ┌─────────┐ ┌────────┐ ┌────────┐  │
│  │ 聊天界面 │ │文件管理│ │文件预览│  │
│  └─────────┘ └────────┘ └────────┘  │
└────────────────┬────────────────────┘
                 │ HTTP / SSE
┌────────────────┴────────────────────┐
│        Spring Boot 后端              │
│  ┌──────────┐ ┌──────────────────┐   │
│  │Agent控制 │ │ 文件下载/内容API │   │
│  └────┬─────┘ └──────────────────┘   │
│       │                              │
│  ┌────┴─────────────────────┐        │
│  │   ReAct Agent 核心       │        │
│  │   (思考-行动-观察循环)    │        │
│  └────┬─────────────────────┘        │
│       │                              │
│  ┌────┴─────────────────────┐        │
│  │   工具层 (Tool Layer)     │        │
│  │ Word / Excel / PPT / 搜索│        │
│  └──────────────────────────┘        │
└────────────────┬────────────────────┘
                 │
┌────────────────┴────────────────────┐
│         DeepSeek / 通义千问 API       │
│         (LangChain4j 集成)           │
└─────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- **Java**: JDK 21+
- **Node.js**: 16.0+
- **Maven**: 3.6+
- **API Key**: DeepSeek 或通义千问 API Key

### 启动步骤

#### 方式一：一键启动（推荐）

双击 `start.bat` 即可自动启动前后端服务。

#### 方式二：手动启动

##### 1. 配置 API Key

```bash
# 复制环境变量模板
copy .env.example .env

# 编辑 .env 文件，填入你的 API Key
# OPENAI_API_KEY=你的真实API Key
```

##### 2. 后端启动
```bash
cd phase3-advance
mvn spring-boot:run
```

##### 3. 前端启动
```bash
cd ai-code-helper-frontend
npm install
npm run dev
```

##### 4. 访问应用
- 前端地址: `http://localhost:3000`
- 后端API: `http://localhost:8081/api`

## 💡 使用示例

### 生成 Word 文档
```
用户: "帮我生成一份关于Java学习的报告"
智能体: 调用 generateWordDocument 工具 → 生成 .docx 文件 → 返回下载链接
```

### 生成 Excel 学习计划
```
用户: "帮我制定一份为期一周的Java学习计划"
智能体: 调用 generateStudyPlan 工具 → 生成 .xlsx 文件 → 返回下载链接
```

### 生成 PPT 演示文稿
```
用户: "帮我生成一份关于Spring Boot的PPT"
智能体: 调用 generatePresentation 工具 → 生成 .pptx 文件 → 返回下载链接
```

## 📁 项目结构

```
phase3-advance/
├── src/main/java/com/yupi/aicodehelper/
│   ├── ai/
│   │   ├── agent/           # ReAct 智能体核心
│   │   │   ├── ReActAgent.java      # 思考-行动-观察循环
│   │   │   ├── AgentStep.java       # 步骤记录
│   │   │   ├── AgentResponse.java   # 响应封装
│   │   │   └── AgentConfig.java     # 智能体配置
│   │   └── tools/           # 工具层
│   │       ├── WordDocumentTool.java   # Word 文档生成
│   │       ├── ExcelDocumentTool.java  # Excel 表格生成
│   │       ├── PptDocumentTool.java    # PPT 演示文稿生成
│   │       ├── InterviewQuestionTool.java # 面试题搜索
│   │       ├── ToolExecutor.java       # 工具执行器
│   │       └── ToolSpecifications.java # 工具规范
│   └── controller/
│       ├── AgentController.java       # 智能体 API
│       ├── FileDownloadController.java # 文件下载
│       └── FileContentController.java  # 文件内容/列表 API
├── ai-code-helper-frontend/
│   └── src/
│       ├── api/
│       │   ├── agentApi.js        # 智能体 API 调用
│       │   └── chatApi.js         # 对话 API 调用
│       └── components/
│           ├── FileManager.vue    # 文件管理面板
│           ├── FilePreview.vue    # 文件在线预览
│           └── AgentThoughtProcess.vue # 思考过程展示
└── start.bat              # 一键启动脚本
```

## 🔧 智能体工作原理

本项目采用 **ReAct (Reasoning + Acting)** 模式：

1. **思考 (Think)**: AI 分析用户需求，决定使用哪个工具
2. **行动 (Act)**: 调用对应的文档生成工具
3. **观察 (Observe)**: 获取工具执行结果
4. **回答 (Answer)**: 根据结果给出最终答案

支持三种工具调用方式：
- **Function Calling**: 优先使用模型的 function calling 机制
- **文本指令**: 解析 `{{工具名:参数}}` 格式的文本指令
- **关键词匹配**: 根据用户输入的关键词自动匹配工具

## 📝 致谢

- [LangChain4j](https://github.com/langchain4j/langchain4j) - 强大的AI应用开发框架
- [Apache POI](https://poi.apache.org/) - Office 文档处理库
- [Spring Boot](https://spring.io/projects/spring-boot) - Java开发框架
- [Vue.js](https://vuejs.org/) - 渐进式JavaScript框架
