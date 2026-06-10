package com.yupi.aicodehelper.ai.tools;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import dev.langchain4j.agent.tool.ToolExecutionRequest;
import lombok.extern.slf4j.Slf4j;

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;

/**
 * 工具执行器 - 负责动态调用工具方法
 */
@Slf4j
public class ToolExecutor {

    private static final Gson gson = new Gson();

    /**
     * 执行指定的工具调用（通过 ToolExecutionRequest）
     *
     * @param tools      工具对象列表
     * @param request    工具执行请求
     * @return 工具执行结果字符串
     * @throws Exception 执行失败时抛出异常
     */
    public static String execute(List<Object> tools, ToolExecutionRequest request) throws Exception {
        String toolName = request.name();
        String arguments = request.arguments();

        // 查找匹配的工具对象和方法
        for (Object tool : tools) {
            for (Method method : tool.getClass().getMethods()) {
                // 检查方法是否有 @Tool 注解
                dev.langchain4j.agent.tool.Tool toolAnnotation = 
                        method.getAnnotation(dev.langchain4j.agent.tool.Tool.class);
                if (toolAnnotation != null) {
                    String annotationName = toolAnnotation.name();
                    if (annotationName.isEmpty()) {
                        annotationName = method.getName();
                    }
                    
                    if (annotationName.equals(toolName)) {
                        // 解析参数并调用方法
                        Object[] args = parseArguments(method, arguments);
                        Object result = method.invoke(tool, args);
                        return result != null ? result.toString() : "执行成功（无返回值）";
                    }
                }
            }
        }

        throw new IllegalArgumentException("未找到工具: " + toolName);
    }

    /**
     * 通过文本格式执行工具调用
     * 格式: {{工具名:参数1|参数2|参数3}}
     * 用于当模型不主动调用 function calling 时的备选方案
     *
     * @param tools    工具对象列表
     * @param toolName 工具名
     * @param argsText 参数字符串（用 | 分隔）
     * @return 工具执行结果
     * @throws Exception 执行失败时抛出异常
     */
    public static String executeByText(List<Object> tools, String toolName, String argsText) throws Exception {
        // 查找匹配的工具对象和方法
        for (Object tool : tools) {
            for (Method method : tool.getClass().getMethods()) {
                dev.langchain4j.agent.tool.Tool toolAnnotation = 
                        method.getAnnotation(dev.langchain4j.agent.tool.Tool.class);
                if (toolAnnotation != null) {
                    String annotationName = toolAnnotation.name();
                    if (annotationName.isEmpty()) {
                        annotationName = method.getName();
                    }
                    
                    if (annotationName.equals(toolName)) {
                        // 解析文本参数并调用方法
                        Object[] args = parseTextArguments(method, argsText);
                        Object result = method.invoke(tool, args);
                        return result != null ? result.toString() : "执行成功（无返回值）";
                    }
                }
            }
        }

        throw new IllegalArgumentException("未找到工具: " + toolName);
    }

    /**
     * 解析文本参数（用 | 分隔）为方法参数数组
     * 支持 String、String[]、String[][] 类型
     */
    private static Object[] parseTextArguments(Method method, String argsText) {
        Class<?>[] paramTypes = method.getParameterTypes();
        if (paramTypes.length == 0) {
            return new Object[0];
        }

        // 按 | 分割参数
        String[] rawArgs = argsText.split("\\|", -1);
        Object[] args = new Object[paramTypes.length];

        for (int i = 0; i < paramTypes.length; i++) {
            if (i >= rawArgs.length) {
                args[i] = null;
                continue;
            }

            String rawValue = rawArgs[i].trim();
            Class<?> paramType = paramTypes[i];

            if (paramType == String.class) {
                args[i] = rawValue.isEmpty() ? null : rawValue;
            } else if (paramType == String[].class) {
                // String[]: 用 | 分割后的剩余部分作为数组
                List<String> list = new ArrayList<>();
                for (int j = i; j < rawArgs.length; j++) {
                    String val = rawArgs[j].trim();
                    if (!val.isEmpty()) {
                        list.add(val);
                    }
                }
                args[i] = list.toArray(new String[0]);
                // 只取第一个参数（数组），后面的参数不再处理
                break;
            } else if (paramType == String[][].class) {
                // String[][]: 用 ; 分割行，用 | 分割列
                String[] rows = rawValue.split(";", -1);
                String[][] result = new String[rows.length][];
                for (int r = 0; r < rows.length; r++) {
                    String[] cols = rows[r].split("\\|", -1);
                    result[r] = cols;
                }
                args[i] = result;
            } else {
                args[i] = rawValue;
            }
        }

        return args;
    }

    /**
     * 解析 JSON 参数为方法参数数组
     * 按 JSON 中 key 的出现顺序匹配到方法参数位置
     */
    private static Object[] parseArguments(Method method, String argumentsJson) {
        Class<?>[] paramTypes = method.getParameterTypes();
        if (paramTypes.length == 0) {
            return new Object[0];
        }

        // 处理空参数
        if (argumentsJson == null || argumentsJson.trim().isEmpty()) {
            Object[] args = new Object[paramTypes.length];
            for (int i = 0; i < paramTypes.length; i++) {
                args[i] = null;
            }
            return args;
        }

        JsonObject jsonArgs;
        try {
            jsonArgs = JsonParser.parseString(argumentsJson).getAsJsonObject();
        } catch (Exception e) {
            log.warn("JSON 参数解析失败: {}, 使用空参数", argumentsJson);
            Object[] args = new Object[paramTypes.length];
            for (int i = 0; i < paramTypes.length; i++) {
                args[i] = null;
            }
            return args;
        }

        Object[] args = new Object[paramTypes.length];

        // 收集 JSON 中所有 key（按插入顺序）
        List<String> jsonKeys = new ArrayList<>();
        for (String key : jsonArgs.keySet()) {
            jsonKeys.add(key);
        }

        java.lang.reflect.Parameter[] parameters = method.getParameters();
        for (int i = 0; i < parameters.length; i++) {
            // 优先从 @P 注解获取参数名
            String paramName = null;
            dev.langchain4j.agent.tool.P pAnnotation = 
                    parameters[i].getAnnotation(dev.langchain4j.agent.tool.P.class);
            if (pAnnotation != null && !pAnnotation.value().isEmpty()) {
                paramName = pAnnotation.value();
            }
            
            // 如果 @P 注解没有值，尝试从方法参数名获取
            if (paramName == null || paramName.isEmpty()) {
                paramName = parameters[i].getName();
            }

            Class<?> paramType = paramTypes[i];
            
            try {
                // 先尝试按参数名匹配
                if (paramName != null && jsonArgs.has(paramName)) {
                    args[i] = gson.fromJson(jsonArgs.get(paramName), paramType);
                } 
                // 如果按名匹配失败，按 JSON key 的顺序位置匹配
                else if (i < jsonKeys.size()) {
                    String key = jsonKeys.get(i);
                    args[i] = gson.fromJson(jsonArgs.get(key), paramType);
                }
                else {
                    args[i] = null;
                }
            } catch (Exception e) {
                log.warn("参数 {} 解析失败: {}", paramName, e.getMessage());
                args[i] = null;
            }
        }

        return args;
    }
}
