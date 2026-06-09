package com.yupi.aicodehelper.ai.agent;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 智能体的完整响应
 * 包含最终答案和完整的思考过程
 */
@Data
@AllArgsConstructor
@NoArgsConstructor
public class AgentResponse {
    /** 最终答案文本 */
    private String finalAnswer;
    
    /** 完整的思考步骤列表 */
    private List<AgentStep> steps;
    
    /** 是否成功完成 */
    private boolean success;

    /** 生成的文件路径列表（用于前端展示下载链接） */
    private List<String> generatedFiles;
}
