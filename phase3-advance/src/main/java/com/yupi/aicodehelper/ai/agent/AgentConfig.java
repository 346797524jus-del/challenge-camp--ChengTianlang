package com.yupi.aicodehelper.ai.agent;

import com.yupi.aicodehelper.ai.memory.ConversationMemory;
import com.yupi.aicodehelper.ai.rag.ContextEnricher;
import com.yupi.aicodehelper.ai.tools.*;
import dev.langchain4j.model.chat.ChatModel;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.Arrays;
import java.util.List;

/**
 * 智能体配置 - 装配所有工具并创建 ReAct 智能体
 * 
 * v2.0 升级：集成 RAG 上下文增强、会话记忆、项目扫描/清洗/合并工具
 */
@Configuration
public class AgentConfig {

    @Bean
    public ReActAgent reActAgent(
            @Qualifier("ollamaChatModel") ChatModel chatModel,
            // 原有工具
            InterviewQuestionTool interviewQuestionTool,
            WordDocumentTool wordDocumentTool,
            ExcelDocumentTool excelDocumentTool,
            PptDocumentTool pptDocumentTool,
            // 新增工具
            ProjectScannerTool projectScannerTool,
            DataCleanTool dataCleanTool,
            FileMergeTool fileMergeTool,
            // RAG + 记忆
            ContextEnricher contextEnricher,
            ConversationMemory conversationMemory) {
        
        // 收集所有工具（共 10 个工具类，提供 16+ 个工具方法）
        List<Object> tools = Arrays.asList(
                // 文档生成类
                interviewQuestionTool,
                wordDocumentTool,
                excelDocumentTool,
                pptDocumentTool,
                // 项目分析类
                projectScannerTool,
                // 数据清洗类
                dataCleanTool,
                // 文件合并类
                fileMergeTool
        );

        return new ReActAgent(chatModel, tools, contextEnricher, conversationMemory);
    }
}
