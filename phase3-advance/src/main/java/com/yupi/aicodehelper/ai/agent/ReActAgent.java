package com.yupi.aicodehelper.ai.agent;

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
 * 采用双重策略：
 * 1. 优先使用模型的 function calling 机制
 * 2. 如果模型不调用工具，则解析文本中的工具调用指令
 */
@Slf4j
@Service
public class ReActAgent {

    private final ChatModel chatModel;
    private final List<Object> tools;
    private static final int MAX_ITERATIONS = 15;

    // 匹配工具调用指令的正则：{{工具名:参数1|参数2|...}}
    private static final Pattern TOOL_CALL_PATTERN = Pattern.compile(
            "\\{\\{\\s*(\\w+)\\s*:\\s*(.*?)\\s*\\}\\}", Pattern.DOTALL);

    private static final String REACT_SYSTEM_PROMPT = """
            你是 AI 编程小助手，一个强大的智能体（Agent），拥有思考和行动能力。
            
            ## 核心原则
            1. 你会收到用户的请求，必须使用可用的工具来完成任务
            2. 分析用户需求后，选择合适的工具并调用它
            3. 每次使用工具后，观察结果，然后决定下一步行动
            4. 当收集到足够信息或完成任务后，给出最终答案
            
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
            1. generateWordDocument(title, paragraphs, author) - 生成 Word 文档
               - title: 文档标题
               - paragraphs: 段落内容数组，用 | 分隔
               - author: 作者名
               
            2. generateResume(name, contactInfo, education, workExperience, skills, projects) - 生成简历
               - name: 姓名
               - contactInfo: 联系方式
               - education: 教育背景数组，用 | 分隔
               - workExperience: 工作经历数组，用 | 分隔
               - skills: 技能数组，用 | 分隔
               - projects: 项目数组，用 | 分隔
               
            3. generateExcelSpreadsheet(fileName, sheetName, columnHeaders, rowData) - 生成 Excel 表格
               - fileName: 文件名
               - sheetName: 工作表名
               - columnHeaders: 列标题数组，用 | 分隔
               - rowData: 行数据数组，每行用 ; 分隔，每行内用 | 分隔
               
            4. generateStudyPlan(title, dailyTasks) - 生成学习计划表
               - title: 计划标题
               - dailyTasks: 每日任务数组，每项格式: 日期|科目|任务|备注
               
            5. generatePresentation(title, slides) - 生成 PPT 演示文稿
               - title: 演示文稿标题
               - slides: 幻灯片数组，每项格式: 幻灯片标题|内容1|内容2|...
               
            6. interviewQuestionSearch(keyword) - 搜索面试题
               - keyword: 搜索关键词
            
            ## 强制要求
            - 当用户要求生成文档/简历/表格/PPT/搜索面试题时，你必须调用对应的工具
            - 调用工具时，必须使用 {{工具名:参数}} 格式
            - 调用工具后，等待工具返回结果，然后根据结果给出最终答案
            - 最终答案必须用中文回复
            - 绝对不要只回复文字而不调用工具
            - 生成文件后，在最终答案中告知用户文件已生成，并说明文件内容和用途
            """;

    public ReActAgent(ChatModel chatModel, List<Object> tools) {
        this.chatModel = chatModel;
        this.tools = tools;
    }

    /**
     * 执行 ReAct 循环
     *
     * @param userMessage 用户消息
     * @return 智能体的完整响应，包含思考过程和最终答案
     */
    public AgentResponse execute(String userMessage) {
        List<AgentStep> steps = new ArrayList<>();
        List<ChatMessage> messages = new ArrayList<>();
        List<String> generatedFiles = new ArrayList<>();

        // 添加系统提示
        messages.add(new SystemMessage(REACT_SYSTEM_PROMPT));
        messages.add(new UserMessage(userMessage));

        // 获取工具定义（用于 function calling）
        List<ToolSpecification> toolSpecifications = ToolSpecifications.from(tools);

        // 标记是否已经成功执行过工具
        boolean toolExecuted = false;

        for (int i = 0; i < MAX_ITERATIONS; i++) {
            log.info("ReAct 迭代 {}/{}", i + 1, MAX_ITERATIONS);

            // 1. 思考：让模型决定下一步
            ChatRequest request = ChatRequest.builder()
                    .messages(messages)
                    .toolSpecifications(toolSpecifications)
                    .toolChoice(ToolChoice.AUTO)
                    .build();

            ChatResponse response = chatModel.chat(request);
            AiMessage aiMessage = response.aiMessage();
            String responseText = aiMessage.text() != null ? aiMessage.text() : "";

            // 记录思考步骤
            AgentStep step = new AgentStep();
            step.setThought(responseText);
            step.setIteration(i + 1);

            // 2. 策略一：检查是否有 function calling 工具调用
            if (aiMessage.hasToolExecutionRequests()) {
                var toolRequests = aiMessage.toolExecutionRequests();
                for (var toolRequest : toolRequests) {
                    step.setAction(toolRequest.name());
                    step.setActionInput(toolRequest.arguments().toString());
                    log.info("Function calling 调用工具: {}，参数: {}", toolRequest.name(), toolRequest.arguments());

                    try {
                        String toolResult = ToolExecutor.execute(tools, toolRequest);
                        step.setObservation(toolResult);
                        log.info("工具结果: {}", toolResult);
                        toolExecuted = true;
                        
                        // 从工具结果中提取文件路径
                        extractFilePath(toolResult, generatedFiles);
                        
                        messages.add(aiMessage);
                        messages.add(new ToolExecutionResultMessage(toolRequest.id(), toolRequest.name(), toolResult));
                    } catch (Exception e) {
                        String errorMsg = "工具执行失败: " + e.getMessage();
                        step.setObservation(errorMsg);
                        log.error(errorMsg, e);
                        messages.add(aiMessage);
                        messages.add(new ToolExecutionResultMessage(toolRequest.id(), toolRequest.name(), errorMsg));
                    }
                }
                steps.add(step);
                continue;
            }

            // 3. 策略二：解析文本中的工具调用指令 {{工具名:参数}}
            Matcher matcher = TOOL_CALL_PATTERN.matcher(responseText);
            if (matcher.find()) {
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

            // 5. 没有工具调用，说明模型给出了最终答案
            step.setFinalAnswer(responseText);
            steps.add(step);
            return new AgentResponse(responseText, steps, true, generatedFiles);
        }

        // 达到最大迭代次数，返回当前结果
        // 如果工具已执行过，说明任务已完成，返回最后一条有意义的响应
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
