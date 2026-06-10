package com.yupi.aicodehelper.controller;

import com.yupi.aicodehelper.ai.agent.AgentResponse;
import com.yupi.aicodehelper.ai.agent.AgentStep;
import com.yupi.aicodehelper.ai.agent.ReActAgent;
import com.yupi.aicodehelper.ai.memory.ConversationMemory;
import com.yupi.aicodehelper.ai.rag.ContextEnricher;
import jakarta.annotation.Resource;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;

import java.util.*;

/**
 * 智能体控制器 - 提供 ReAct 智能体的 API 接口
 * 
 * v2.0 升级：支持用户ID、会话记忆、RAG检索
 */
@RestController
@RequestMapping("/agent")
public class AgentController {

    @Resource
    private ReActAgent reActAgent;

    @Resource
    private ConversationMemory conversationMemory;

    @Resource
    private ContextEnricher contextEnricher;

    /**
     * 智能体对话接口（非流式）
     * 支持 userId 参数用于个性化上下文增强
     */
    @PostMapping("/chat")
    public AgentResponse chat(@RequestBody Map<String, String> request) {
        String message = request.get("message");
        String userId = request.getOrDefault("userId", "default-user");
        
        if (message == null || message.trim().isEmpty()) {
            return new AgentResponse("请输入消息", List.of(), false, List.of());
        }
        
        // 执行智能体（带用户ID）
        AgentResponse response = reActAgent.execute(message, userId);
        
        // 记录对话到记忆
        if (response.isSuccess() && response.getFinalAnswer() != null) {
            try {
                conversationMemory.recordExchange(userId, message, response.getFinalAnswer());
            } catch (Exception e) {
                // 记忆记录失败不影响主流程
            }
        }
        
        return response;
    }

    /**
     * 智能体对话接口（流式）
     * 逐步返回智能体的思考过程
     */
    @GetMapping("/chat/stream")
    public Flux<ServerSentEvent<String>> chatStream(
            @RequestParam String message,
            @RequestParam(defaultValue = "default-user") String userId) {
        AgentResponse response = reActAgent.execute(message, userId);
        
        // 记录对话
        if (response.isSuccess() && response.getFinalAnswer() != null) {
            try {
                conversationMemory.recordExchange(userId, message, response.getFinalAnswer());
            } catch (Exception ignored) {}
        }
        
        return Flux.fromIterable(response.getSteps())
                .map(step -> ServerSentEvent.<String>builder()
                        .event("step")
                        .data(stepToJson(step))
                        .build())
                .concatWithValues(
                        ServerSentEvent.<String>builder()
                                .event("final")
                                .data(response.getFinalAnswer())
                                .build()
                );
    }

    /**
     * 获取智能体可用的工具列表
     */
    @GetMapping("/tools")
    public Map<String, Object> getAvailableTools() {
        List<Map<String, String>> tools = new ArrayList<>();
        
        tools.add(createToolInfo("interviewQuestionSearch", "搜索面试题", "检索与查询"));
        tools.add(createToolInfo("generateWordDocument", "生成 Word 文档", "文档生成"));
        tools.add(createToolInfo("generateResume", "生成简历", "文档生成"));
        tools.add(createToolInfo("generateExcelSpreadsheet", "生成 Excel 表格", "文档生成"));
        tools.add(createToolInfo("generateStudyPlan", "生成学习计划表", "文档生成"));
        tools.add(createToolInfo("generatePresentation", "生成 PPT 演示文稿", "文档生成"));
        tools.add(createToolInfo("scanProjectStructure", "扫描项目文件结构", "项目分析"));
        tools.add(createToolInfo("analyzeProjectDeep", "深度分析项目", "项目分析"));
        tools.add(createToolInfo("cleanCsvData", "清洗 CSV 数据", "数据清洗"));
        tools.add(createToolInfo("cleanJsonlData", "清洗 JSONL 数据", "数据清洗"));
        tools.add(createToolInfo("cleanTextFile", "清洗文本文件", "数据清洗"));
        tools.add(createToolInfo("scanAndCleanDirectory", "扫描目录数据质量", "数据清洗"));
        tools.add(createToolInfo("mergeCsvFiles", "合并 CSV 文件", "文件合并"));
        tools.add(createToolInfo("mergeJsonlFiles", "合并 JSONL 文件", "文件合并"));
        tools.add(createToolInfo("mergeTextFiles", "合并文本文件", "文件合并"));
        tools.add(createToolInfo("mergeDirectoryFiles", "按类型合并目录文件", "文件合并"));
        
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("total", tools.size());
        result.put("tools", tools);
        return result;
    }

    /**
     * RAG 检索接口 - 从知识库和偏好中检索信息
     */
    @GetMapping("/search")
    public Map<String, Object> search(
            @RequestParam String query,
            @RequestParam(defaultValue = "5") int maxResults) {
        String result = contextEnricher.quickSearch(query, maxResults);
        Map<String, Object> response = new LinkedHashMap<>();
        response.put("query", query);
        response.put("result", result);
        response.put("isEmpty", result == null || result.isEmpty());
        return response;
    }

    /**
     * 获取用户记忆统计
     */
    @GetMapping("/memory/stats")
    public Map<String, Object> getMemoryStats(
            @RequestParam(defaultValue = "default-user") String userId) {
        return conversationMemory.getStats(userId);
    }

    /**
     * 清除用户短时记忆（开始新会话）
     */
    @PostMapping("/memory/clear")
    public Map<String, String> clearMemory(@RequestBody Map<String, String> request) {
        String userId = request.getOrDefault("userId", "default-user");
        conversationMemory.clearShortTerm(userId);
        return Map.of("status", "ok", "message", "短时记忆已清除", "userId", userId);
    }

    /**
     * 将 AgentStep 转换为 JSON 字符串
     */
    private String stepToJson(AgentStep step) {
        StringBuilder json = new StringBuilder();
        json.append("{");
        json.append("\"iteration\":").append(step.getIteration()).append(",");
        json.append("\"thought\":\"").append(escapeJson(step.getThought())).append("\",");
        json.append("\"action\":\"").append(escapeJson(step.getAction())).append("\",");
        json.append("\"actionInput\":\"").append(escapeJson(step.getActionInput())).append("\",");
        json.append("\"observation\":\"").append(escapeJson(step.getObservation())).append("\",");
        json.append("\"finalAnswer\":\"").append(escapeJson(step.getFinalAnswer())).append("\"");
        json.append("}");
        return json.toString();
    }

    private String escapeJson(String value) {
        if (value == null) return "";
        return value
                .replace("\\", "\\\\")
                .replace("\"", "\\\"")
                .replace("\n", "\\n")
                .replace("\r", "\\r")
                .replace("\t", "\\t");
    }

    private Map<String, String> createToolInfo(String name, String description, String category) {
        Map<String, String> info = new LinkedHashMap<>();
        info.put("name", name);
        info.put("description", description);
        info.put("category", category);
        return info;
    }
}
