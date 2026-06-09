package com.yupi.aicodehelper.controller;

import com.yupi.aicodehelper.ai.agent.AgentResponse;
import com.yupi.aicodehelper.ai.agent.AgentStep;
import com.yupi.aicodehelper.ai.agent.ReActAgent;
import jakarta.annotation.Resource;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;

import java.util.List;
import java.util.Map;

/**
 * 智能体控制器 - 提供 ReAct 智能体的 API 接口
 */
@RestController
@RequestMapping("/agent")
public class AgentController {

    @Resource
    private ReActAgent reActAgent;

    /**
     * 智能体对话接口（非流式）
     * 返回智能体的思考过程和最终答案
     */
    @PostMapping("/chat")
    public AgentResponse chat(@RequestBody Map<String, String> request) {
        String message = request.get("message");
        if (message == null || message.trim().isEmpty()) {
            return new AgentResponse("请输入消息", List.of(), false, List.of());
        }
        return reActAgent.execute(message);
    }

    /**
     * 智能体对话接口（流式）
     * 逐步返回智能体的思考过程
     */
    @GetMapping("/chat/stream")
    public Flux<ServerSentEvent<String>> chatStream(@RequestParam String message) {
        AgentResponse response = reActAgent.execute(message);
        
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
    public List<String> getAvailableTools() {
        return List.of(
                "interviewQuestionSearch - 搜索面试题",
                "generateWordDocument - 生成 Word 文档",
                "generateResume - 生成简历",
                "generateExcelSpreadsheet - 生成 Excel 表格",
                "generateStudyPlan - 生成学习计划表",
                "generatePresentation - 生成 PPT 演示文稿"
        );
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
}
