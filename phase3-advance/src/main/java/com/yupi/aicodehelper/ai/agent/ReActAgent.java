package com.yupi.aicodehelper.ai.agent;

import com.yupi.aicodehelper.ai.memory.ConversationMemory;
import com.yupi.aicodehelper.ai.rag.ContextEnricher;
import com.yupi.aicodehelper.ai.tools.ToolExecutor;
import com.yupi.aicodehelper.ai.tools.ToolSpecifications;
import dev.langchain4j.agent.tool.ToolSpecification;
import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.message.ChatMessage;
import dev.langchain4j.data.message.SystemMessage;
import dev.langchain4j.data.message.ToolExecutionResultMessage;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.model.chat.request.ToolChoice;
import dev.langchain4j.model.chat.response.ChatResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * ReAct 智能体核心 - 实现思考-行动-观察循环
 * 让 AI 能够自主分析问题、调用工具、观察结果并给出最终答案
 * 
 * 集成 RAG 检索增强、用户偏好感知、会话记忆
 * 
 * 采用双重策略：
 * 1. 优先使用模型的 function calling 机制
 * 2. 如果模型不调用工具，则解析文本中的工具调用指令
 */
@Slf4j
@Service
public class ReActAgent {

    private final ChatModel chatModel;
    private final List<Object> tools;
    private final ContextEnricher contextEnricher;
    private final ConversationMemory conversationMemory;
    private static final int MAX_ITERATIONS = 10;

    // 匹配工具调用指令的正则：{{工具名:参数1|参数2|...}}
    private static final Pattern TOOL_CALL_PATTERN = Pattern.compile(
            "\\{\\{\\s*(\\w+)\\s*:\\s*(.*?)\\s*\\}\\}", Pattern.DOTALL);

    private static final String REACT_SYSTEM_PROMPT = """
            你是 AI 智能助手，一个强大的智能体（Agent），拥有思考、检索和行动能力。
            
            ## 核心原则
            1. 你会收到用户的请求，必须使用可用的工具来完成任务
            2. 分析用户需求后，选择合适的工具并调用它
            3. 每次使用工具后，观察结果，然后决定下一步行动
            4. 当收集到足够信息或完成任务后，给出最终答案
            5. 优先参考提供的上下文信息（知识库、用户偏好、历史记忆）
            
            ## 工作流程（必须严格遵守）
            你必须按以下流程工作：
            
            第一步：分析用户需求，确定需要使用的工具
            第二步：调用工具
            第三步：查看工具返回的结果
            第四步：如果任务完成，给出最终答案；否则继续调用工具
            
            ## 如何调用工具
            在回复中，使用以下格式来调用工具：
            {{工具名:参数1|参数2|参数3}}
            
            例如，要生成 Word 文档：
            {{generateWordDocument:AI编程小助手介绍|这是一份关于AI编程小助手的文档。|AI助手}}
            
            可用工具列表：
            【文档生成类】
            1. generateWordDocument(title, paragraphs, author) - 生成 Word 文档
            2. generateResume(name, contactInfo, education, workExperience, skills, projects) - 生成简历
            3. generateExcelSpreadsheet(fileName, sheetName, columnHeaders, rowData) - 生成 Excel 表格
            4. generateStudyPlan(title, dailyTasks) - 生成学习计划表
            5. generatePresentation(title, slides) - 生成 PPT 演示文稿
            
            【检索与查询类】
            6. interviewQuestionSearch(keyword) - 搜索面试题
            
            【项目扫描与分析类】
            7. scanProjectStructure(directoryPath, recursive) - 扫描项目文件结构
            8. analyzeProjectDeep(directoryPath, focus) - 深度分析项目
            
            【数据清洗类】
            9. cleanCsvData(filePath, removeDuplicates, removeEmptyRows) - 清洗CSV数据
            10. cleanJsonlData(filePath) - 清洗JSONL数据
            11. cleanTextFile(filePath, removeEmptyLines) - 清洗文本文件
            12. scanAndCleanDirectory(directoryPath) - 扫描目录数据质量
            
            【文件合并类】
            13. mergeCsvFiles(filePaths, includeAllHeaders) - 合并多个CSV文件
            14. mergeJsonlFiles(filePaths) - 合并多个JSONL文件
            15. mergeTextFiles(filePaths, addFileHeaders) - 合并多个文本文件
            16. mergeDirectoryFiles(directoryPath, extension, recursive) - 按类型合并目录文件
            
            ## 强制要求
            - 当用户要求生成文档/简历/表格/PPT/搜索面试题/扫描项目/清洗数据/合并文件时，你必须调用对应的工具
            - 调用工具时，必须使用 {{工具名:参数}} 格式
            - 调用工具后，等待工具返回结果，然后根据结果给出最终答案
            - 最终答案必须用中文回复
            - 绝对不要只回复文字而不调用工具
            - 生成文件后，在最终答案中告知用户文件已生成，并说明文件内容和用途
            - 如果用户偏好中有相关设置（如输出风格、语言偏好），请严格遵守
            """;

    public ReActAgent(ChatModel chatModel, List<Object> tools, 
                       ContextEnricher contextEnricher, 
                       ConversationMemory conversationMemory) {
        this.chatModel = chatModel;
        this.tools = tools;
        this.contextEnricher = contextEnricher;
        this.conversationMemory = conversationMemory;
    }

    /**
     * 执行 ReAct 循环（无用户ID，使用简化模式）
     */
    public AgentResponse execute(String userMessage) {
        return execute(userMessage, null);
    }

    /**
     * 执行 ReAct 循环（带用户ID，启用完整上下文增强和记忆）
     *
     * @param userMessage 用户消息
     * @param userId      用户标识
     * @return 智能体的完整响应，包含思考过程和最终答案
     */
    public AgentResponse execute(String userMessage, String userId) {
        List<AgentStep> steps = new ArrayList<>();
        List<ChatMessage> messages = new ArrayList<>();
        List<String> generatedFiles = new ArrayList<>();

        // 🔥 增强系统提示：注入用户偏好、知识库、记忆上下文
        String enrichedPrompt = REACT_SYSTEM_PROMPT;
        if (userId != null && !userId.isEmpty()) {
            try {
                // 1. 注入 RAG 检索上下文（偏好 + 知识库）
                enrichedPrompt = contextEnricher.enrichSystemPrompt(userMessage, userId, REACT_SYSTEM_PROMPT);
                log.info("已增强系统提示，长度: {}", enrichedPrompt.length());
                
                // 2. 注入会话记忆上下文
                String memoryContext = conversationMemory.getMemoryContext(userId, userMessage);
                if (!memoryContext.isEmpty()) {
                    enrichedPrompt += "\n\n## 🧠 会话记忆\n" + memoryContext;
                }
            } catch (Exception e) {
                log.warn("上下文增强失败，使用基础提示: {}", e.getMessage());
            }
        }

        // 添加增强后的系统提示
        messages.add(new SystemMessage(enrichedPrompt));
        messages.add(new UserMessage(userMessage));

        // 获取工具定义（用于 function calling）
        List<ToolSpecification> toolSpecifications = ToolSpecifications.from(tools);

        // 标记是否已经成功执行过工具
        boolean toolExecuted = false;
        // 记录连续无工具调用的次数，防止死循环
        int noToolCallCount = 0;

        for (int i = 0; i < MAX_ITERATIONS; i++) {
            log.info("ReAct 迭代 {}/{}", i + 1, MAX_ITERATIONS);

            // 1. 思考：让模型决定下一步
            ChatRequest request = ChatRequest.builder()
                    .messages(messages)
                    .toolSpecifications(toolSpecifications)
                    .toolChoice(ToolChoice.AUTO)
                    .build();

            ChatResponse response;
            try {
                response = chatModel.chat(request);
            } catch (Exception e) {
                log.error("AI 模型调用失败: {}", e.getMessage());
                String errorDetail = e.getMessage();
                
                // 检测认证错误，给出更友好的提示
                if (errorDetail != null && errorDetail.contains("Authentication")) {
                    errorDetail = "API 认证失败！请检查以下几点：\n"
                            + "1. 确保 .env 文件中的 OPENAI_API_KEY 是正确的 DeepSeek API Key\n"
                            + "2. 确保 API Key 没有过期\n"
                            + "3. 检查 AI_API_BASE_URL 是否正确（当前: " + System.getenv("AI_API_BASE_URL") + "）\n"
                            + "4. 检查 AI_MODEL_NAME 是否正确（当前: " + System.getenv("AI_MODEL_NAME") + "）\n"
                            + "原始错误: " + errorDetail;
                }
                
                // 如果已经执行过工具，返回部分结果
                if (toolExecuted) {
                    String partialResult = "AI 模型调用出错，但部分工具已执行完成。\n" + errorDetail;
                    AgentStep errorStep = new AgentStep();
                    errorStep.setIteration(i + 1);
                    errorStep.setThought("AI 模型调用失败");
                    errorStep.setObservation(errorDetail);
                    errorStep.setFinalAnswer(partialResult);
                    steps.add(errorStep);
                    return new AgentResponse(partialResult, steps, true, generatedFiles);
                }
                AgentStep errorStep = new AgentStep();
                errorStep.setIteration(i + 1);
                errorStep.setThought("AI 模型调用失败");
                errorStep.setObservation(errorDetail);
                errorStep.setFinalAnswer(errorDetail);
                steps.add(errorStep);
                return new AgentResponse(errorDetail, steps, false, generatedFiles);
            }

            AiMessage aiMessage = response.aiMessage();
            String responseText = aiMessage.text() != null ? aiMessage.text() : "";

            // 记录思考步骤
            AgentStep step = new AgentStep();
            step.setThought(responseText);
            step.setIteration(i + 1);

            // 2. 策略一：检查是否有 function calling 工具调用
            if (aiMessage.hasToolExecutionRequests()) {
                noToolCallCount = 0;
                var toolRequests = aiMessage.toolExecutionRequests();
                
                // 先执行所有工具，收集结果
                List<ToolExecutionResultMessage> toolResults = new java.util.ArrayList<>();
                for (var toolRequest : toolRequests) {
                    log.info("Function calling 调用工具: {}，参数: {}", toolRequest.name(), toolRequest.arguments());
                    try {
                        String toolResult = ToolExecutor.execute(tools, toolRequest);
                        log.info("工具结果: {}", toolResult);
                        toolExecuted = true;
                        
                        // 从工具结果中提取文件路径
                        extractFilePath(toolResult, generatedFiles);
                        
                        toolResults.add(new ToolExecutionResultMessage(toolRequest.id(), toolRequest.name(), toolResult));
                    } catch (Exception e) {
                        String errorMsg = "工具执行失败: " + e.getMessage();
                        log.error(errorMsg, e);
                        toolResults.add(new ToolExecutionResultMessage(toolRequest.id(), toolRequest.name(), errorMsg));
                    }
                }
                
                // 一次性添加 aiMessage 和所有 tool results（保持消息序列正确）
                messages.add(aiMessage);
                for (var tr : toolResults) {
                    messages.add(tr);
                }
                
                // 记录步骤
                step.setAction(toolRequests.get(0).name());
                step.setActionInput(toolRequests.get(0).arguments().toString());
                step.setObservation("已执行 " + toolRequests.size() + " 个工具调用");
                steps.add(step);
                continue;
            }

            // 3. 策略二：解析文本中的工具调用指令 {{工具名:参数}}
            Matcher matcher = TOOL_CALL_PATTERN.matcher(responseText);
            if (matcher.find()) {
                noToolCallCount = 0;
                String toolName = matcher.group(1).trim();
                String toolArgs = matcher.group(2).trim();
                step.setAction(toolName);
                step.setActionInput(toolArgs);
                log.info("文本指令调用工具: {}，参数: {}", toolName, toolArgs);

                try {
                    String parsedResult = ToolExecutor.executeByText(tools, toolName, toolArgs);
                    step.setObservation(parsedResult);
                    log.info("工具结果: {}", parsedResult);
                    toolExecuted = true;
                    
                    // 从工具结果中提取文件路径
                    extractFilePath(parsedResult, generatedFiles);
                    
                    // 将工具结果作为系统消息添加到对话中
                    messages.add(aiMessage);
                    messages.add(new UserMessage("工具 " + toolName + " 执行结果: " + parsedResult + 
                            "\n请根据这个结果给出最终答案。如果还需要其他操作，请继续调用工具。"));
                } catch (Exception e) {
                    String errorMsg = "工具执行失败: " + e.getMessage();
                    step.setObservation(errorMsg);
                    log.error(errorMsg, e);
                    messages.add(aiMessage);
                    messages.add(new UserMessage("工具 " + toolName + " 执行失败: " + errorMsg + 
                            "\n请尝试其他方法或告诉用户。"));
                }
                steps.add(step);
                continue;
            }

            // 4. 策略三：关键词自动匹配工具（仅在第一次迭代且工具未执行过时触发）
            if (!toolExecuted && i == 0) {
                String autoToolName = autoDetectTool(userMessage);
                if (autoToolName != null) {
                    log.info("关键词自动匹配工具: {}", autoToolName);
                    step.setAction(autoToolName);
                    step.setActionInput("自动匹配（由系统根据用户关键词触发）");
                    
                    // 构造一个简单的参数提示，让模型在下一轮调用工具
                    messages.add(aiMessage);
                    messages.add(new UserMessage("注意：用户要求的是生成文档/表格/PPT/搜索面试题等操作，你必须调用对应的工具来完成。"
                            + "请立即调用 " + autoToolName + " 工具来响应用户的请求。不要只回复文字。"));
                    steps.add(step);
                    continue;
                }
            }

            // 5. 没有工具调用，检查是否应该结束
            noToolCallCount++;
            if (noToolCallCount >= 2 && toolExecuted) {
                // 连续两次没有工具调用且已执行过工具，认为任务完成
                step.setFinalAnswer(responseText);
                steps.add(step);
                log.info("连续无工具调用，任务完成");
                return new AgentResponse(responseText, steps, true, generatedFiles);
            }

            // 如果还没有执行过工具，再给一次机会
            if (!toolExecuted && i < MAX_ITERATIONS - 1) {
                messages.add(aiMessage);
                messages.add(new UserMessage("请分析用户需求并调用合适的工具来完成任务。不要只回复文字。"));
                steps.add(step);
                continue;
            }

            // 6. 模型给出了最终答案
            step.setFinalAnswer(responseText);
            steps.add(step);
            return new AgentResponse(responseText, steps, true, generatedFiles);
        }

        // 达到最大迭代次数，返回当前结果
        if (toolExecuted && !steps.isEmpty()) {
            AgentStep lastStep = steps.get(steps.size() - 1);
            String lastResponse = lastStep.getFinalAnswer();
            if (lastResponse != null && !lastResponse.isEmpty()) {
                return new AgentResponse(lastResponse, steps, true, generatedFiles);
            }
        }
        String fallback = "我已经尽力处理您的请求，但可能需要更多信息。请告诉我您还需要什么帮助？";
        return new AgentResponse(fallback, steps, false, generatedFiles);
    }

    /**
     * 从工具执行结果中提取文件路径
     */
    private void extractFilePath(String toolResult, List<String> generatedFiles) {
        if (toolResult == null || toolResult.isEmpty()) return;
        
        // 查找文件路径模式：盘符:\路径\文件名.扩展名
        Pattern filePathPattern = Pattern.compile("[A-Za-z]:\\\\[^\\s]+?\\.(docx|xlsx|pptx)");
        Matcher matcher = filePathPattern.matcher(toolResult);
        while (matcher.find()) {
            String filePath = matcher.group().trim();
            if (!generatedFiles.contains(filePath)) {
                generatedFiles.add(filePath);
                log.info("提取到生成文件: {}", filePath);
            }
        }
    }

    /**
     * 根据用户消息自动检测应该使用的工具
     * 当模型没有主动调用工具时，由系统自动匹配
     */
    private String autoDetectTool(String userMessage) {
        String msg = userMessage.toLowerCase();
        
        // 简历相关
        if (containsAny(msg, "简历", "resume", "cv", "求职", "应聘")) {
            return "generateResume";
        }
        // Word 文档相关
        if (containsAny(msg, "word", "文档", "doc", "报告", "文章", "写一篇", "生成文档")) {
            return "generateWordDocument";
        }
        // Excel 表格相关
        if (containsAny(msg, "excel", "表格", "电子表格", "xlsx", "数据表", "报表")) {
            return "generateExcelSpreadsheet";
        }
        // 学习计划相关
        if (containsAny(msg, "学习计划", "学习安排", "study plan", "学习规划", "日程")) {
            return "generateStudyPlan";
        }
        // PPT 相关
        if (containsAny(msg, "ppt", "演示文稿", "幻灯片", "presentation", "课件", "演讲")) {
            return "generatePresentation";
        }
        // 面试题相关
        if (containsAny(msg, "面试", "interview", "面试题", "面试问题", "考题")) {
            return "interviewQuestionSearch";
        }
        
        return null;
    }

    private boolean containsAny(String text, String... keywords) {
        for (String keyword : keywords) {
            if (text.contains(keyword)) {
                return true;
            }
        }
        return false;
    }

    /**
     * 获取智能体的思考过程（用于前端展示）
     */
    public List<AgentStep> getThoughtProcess(String userMessage) {
        return execute(userMessage).getSteps();
    }
}
