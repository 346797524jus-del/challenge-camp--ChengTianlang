package com.yupi.aicodehelper.ai.tools;

import dev.langchain4j.agent.tool.ToolSpecification;

import java.util.ArrayList;
import java.util.List;

/**
 * 工具规范工具类 - 从工具对象中提取工具定义
 */
public class ToolSpecifications {

    /**
     * 从工具对象列表中提取所有工具规范
     *
     * @param tools 工具对象列表
     * @return 工具规范列表
     */
    public static List<ToolSpecification> from(List<Object> tools) {
        List<ToolSpecification> specifications = new ArrayList<>();
        for (Object tool : tools) {
            // 使用 LangChain4j 的 ToolSpecifications 来提取工具定义
            specifications.addAll(dev.langchain4j.agent.tool.ToolSpecifications.toolSpecificationsFrom(tool));
        }
        return specifications;
    }
}
