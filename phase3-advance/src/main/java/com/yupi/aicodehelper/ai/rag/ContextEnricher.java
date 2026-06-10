package com.yupi.aicodehelper.ai.rag;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import jakarta.annotation.Resource;
import java.util.*;

/**
 * 上下文增强器 - 将 RAG 检索结果、用户偏好和项目数据注入智能体上下文
 * 
 * 核心功能：
 * 1. 根据用户问题自动检索相关知识库
 * 2. 注入用户偏好到系统提示
 * 3. 格式化上下文为 AI 可理解的文本
 */
@Slf4j
@Service
public class ContextEnricher {

    @Resource
    private DataLoader dataLoader;

    private static final int MAX_KNOWLEDGE_RESULTS = 5;
    private static final int MAX_CHAT_RESULTS = 3;
    private static final int MAX_TOOL_RESULTS = 3;

    /**
     * 构建增强后的系统提示词
     * 将用户偏好、知识库检索结果、历史对话等信息注入
     * 
     * @param userMessage 用户当前消息
     * @param userId      用户标识
     * @param basePrompt  基础系统提示
     * @return 增强后的系统提示
     */
    public String enrichSystemPrompt(String userMessage, String userId, String basePrompt) {
        StringBuilder enriched = new StringBuilder(basePrompt);

        // 1. 注入全局上下文
        String globalContext = dataLoader.getSystemContext();
        if (globalContext != null && !globalContext.isEmpty()) {
            enriched.append("\n\n## 📋 系统上下文（用户偏好与配置）\n");
            enriched.append(globalContext);
        }

        // 2. 注入用户特定偏好
        if (userId != null && !userId.isEmpty()) {
            String userPrefs = buildUserPreferenceContext(userId);
            if (!userPrefs.isEmpty()) {
                enriched.append("\n\n## 👤 当前用户偏好\n");
                enriched.append(userPrefs);
            }
        }

        // 3. 注入知识库检索结果
        String knowledgeContext = buildKnowledgeContext(userMessage);
        if (!knowledgeContext.isEmpty()) {
            enriched.append("\n\n## 📚 相关知识库内容\n");
            enriched.append(knowledgeContext);
        }

        // 4. 注入历史对话上下文
        String chatContext = buildChatHistoryContext(userMessage);
        if (!chatContext.isEmpty()) {
            enriched.append("\n\n## 💬 相关历史对话\n");
            enriched.append(chatContext);
        }

        // 5. 注入工具使用历史
        String toolHistoryContext = buildToolHistoryContext(userMessage);
        if (!toolHistoryContext.isEmpty()) {
            enriched.append("\n\n## 🔧 工具使用历史\n");
            enriched.append(toolHistoryContext);
        }

        // 6. 添加检索增强指令
        enriched.append("\n\n## 🧠 检索增强指令\n");
        enriched.append("- 上方提供了与用户相关的知识库、偏好和历史信息\n");
        enriched.append("- 回答问题时请优先参考这些上下文信息\n");
        enriched.append("- 如果用户偏好中有相关设置，请严格遵守\n");
        enriched.append("- 可以利用知识库中的信息来生成更准确的内容\n");

        log.info("上下文增强完成，原始提示长度: {}, 增强后长度: {}", basePrompt.length(), enriched.length());
        return enriched.toString();
    }

    /**
     * 构建用户偏好上下文
     */
    private String buildUserPreferenceContext(String userId) {
        StringBuilder sb = new StringBuilder();
        List<DataLoader.PreferenceEntry> userPrefs = dataLoader.getUserPreferences(userId);

        if (userPrefs.isEmpty()) {
            // 尝试获取系统默认偏好
            List<DataLoader.PreferenceEntry> allPrefs = dataLoader.getAllPreferences();
            List<DataLoader.PreferenceEntry> defaults = allPrefs.stream()
                    .filter(p -> "SYSTEM_DEFAULT".equals(p.getUid()))
                    .limit(10)
                    .collect(java.util.stream.Collectors.toList());
            if (!defaults.isEmpty()) {
                sb.append("（使用系统默认偏好）\n");
                for (DataLoader.PreferenceEntry p : defaults) {
                    sb.append("- ").append(p.getPrefKey()).append(": ").append(p.getPrefValue()).append("\n");
                }
            }
            return sb.toString();
        }

        // 分组展示用户偏好
        Map<String, List<DataLoader.PreferenceEntry>> grouped = userPrefs.stream()
                .collect(java.util.stream.Collectors.groupingBy(
                        p -> p.getPreferenceCategory() != null ? p.getPreferenceCategory() : "其他"));

        for (Map.Entry<String, List<DataLoader.PreferenceEntry>> entry : grouped.entrySet()) {
            sb.append("【").append(entry.getKey()).append("】\n");
            for (DataLoader.PreferenceEntry p : entry.getValue()) {
                sb.append("- ").append(p.getPrefKey()).append(": ").append(p.getPrefValue());
                if (p.getNote() != null && !p.getNote().isEmpty()) {
                    sb.append(" (备注: ").append(p.getNote()).append(")");
                }
                sb.append("\n");
            }
        }

        return sb.toString();
    }

    /**
     * 构建知识库检索上下文
     */
    private String buildKnowledgeContext(String userMessage) {
        List<DataLoader.KnowledgeEntry> results = dataLoader.searchKnowledge(userMessage, MAX_KNOWLEDGE_RESULTS);
        if (results.isEmpty()) return "";

        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < results.size(); i++) {
            DataLoader.KnowledgeEntry entry = results.get(i);
            sb.append(i + 1).append(". **").append(entry.getTitle()).append("**\n");
            if (entry.getTags() != null && !entry.getTags().isEmpty()) {
                sb.append("   标签: ").append(String.join(", ", entry.getTags())).append("\n");
            }
            if (entry.getBodySteps() != null && !entry.getBodySteps().isEmpty()) {
                String body = entry.getBodySteps();
                if (body.length() > 300) {
                    body = body.substring(0, 300) + "...";
                }
                sb.append("   内容: ").append(body).append("\n");
            }
        }
        return sb.toString();
    }

    /**
     * 构建历史聊天上下文
     */
    private String buildChatHistoryContext(String userMessage) {
        List<DataLoader.ChatLogEntry> results = dataLoader.searchChatLogs(userMessage, MAX_CHAT_RESULTS);
        if (results.isEmpty()) return "";

        StringBuilder sb = new StringBuilder();
        for (DataLoader.ChatLogEntry entry : results) {
            sb.append("- [").append(entry.getSession()).append("] ")
                    .append(entry.getRole()).append(": ");
            String text = entry.getText();
            if (text != null) {
                sb.append(text.length() > 150 ? text.substring(0, 150) + "..." : text);
            }
            sb.append("\n");
        }
        return sb.toString();
    }

    /**
     * 构建工具使用历史上下文
     */
    private String buildToolHistoryContext(String userMessage) {
        List<DataLoader.ToolResultEntry> results = dataLoader.searchToolResults(userMessage, MAX_TOOL_RESULTS);
        if (results.isEmpty()) return "";

        StringBuilder sb = new StringBuilder();
        for (DataLoader.ToolResultEntry entry : results) {
            sb.append("- ").append(entry.getTool())
                    .append(" [状态: ").append(entry.getStatus()).append("]");
            if (entry.getRawOutput() != null && !entry.getRawOutput().isEmpty()) {
                String output = entry.getRawOutput();
                if (output.length() > 100) {
                    output = output.substring(0, 100) + "...";
                }
                sb.append(" -> ").append(output);
            }
            sb.append("\n");
        }
        return sb.toString();
    }

    /**
     * 快速检索 - 仅返回检索摘要（用于非 dialogue 场景）
     */
    public String quickSearch(String query, int maxResults) {
        return dataLoader.comprehensiveSearch(query, maxResults);
    }
}