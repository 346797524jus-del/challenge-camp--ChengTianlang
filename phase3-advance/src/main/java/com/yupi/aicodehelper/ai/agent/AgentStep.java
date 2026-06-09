package com.yupi.aicodehelper.ai.agent;

import lombok.Data;

/**
 * 智能体的单个思考-行动-观察步骤
 * 用于记录和展示 AI 的推理过程
 */
@Data
public class AgentStep {
    /** 当前迭代次数 */
    private int iteration;
    
    /** AI 的思考内容 */
    private String thought;
    
    /** 采取的行动（调用的工具名） */
    private String action;
    
    /** 行动的输入参数 */
    private String actionInput;
    
    /** 观察到的结果 */
    private String observation;
    
    /** 最终答案（如果是最后一步） */
    private String finalAnswer;
    
    /** 步骤类型：thought, action, observation, final_answer */
    private String type;
    
    /** 时间戳 */
    private long timestamp = System.currentTimeMillis();
}
