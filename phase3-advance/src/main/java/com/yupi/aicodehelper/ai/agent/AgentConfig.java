package com.yupi.aicodehelper.ai.agent;

import com.yupi.aicodehelper.ai.tools.*;
import dev.langchain4j.model.chat.ChatModel;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Arrays;
import java.util.List;

/**
 * 智能体配置 - 装配所有工具并创建 ReAct 智能体
 */
@Configuration
public class AgentConfig {

    @Bean
    public ReActAgent reActAgent(
            @Qualifier("ollamaChatModel") ChatModel chatModel,
            InterviewQuestionTool interviewQuestionTool,
            WordDocumentTool wordDocumentTool,
            ExcelDocumentTool excelDocumentTool,
            PptDocumentTool pptDocumentTool) {
        
        // 收集所有工具
        List<Object> tools = Arrays.asList(
                interviewQuestionTool,
                wordDocumentTool,
                excelDocumentTool,
                pptDocumentTool
        );

        return new ReActAgent(chatModel, tools);
    }
}
