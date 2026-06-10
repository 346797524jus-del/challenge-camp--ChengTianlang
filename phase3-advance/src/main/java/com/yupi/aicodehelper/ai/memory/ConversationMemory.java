package com.yupi.aicodehelper.ai.memory;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.reflect.TypeToken;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.IOException;
import java.lang.reflect.Type;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * 会话记忆服务 - 跨对话保持记忆
 * 
 * 功能：
 * 1. 存储对话摘要
 * 2. 记录用户问题模式
 * 3. 学习用户偏好
 * 4. 持久化到磁盘
 */
@Slf4j
@Service
public class ConversationMemory {

    private final Gson gson = new GsonBuilder().setPrettyPrinting().create();

    @Value("${data.memory.path:data/memory}")
    private String memoryPath;

    // 会话记忆映射: userId -> List<MemoryEntry>
    private final Map<String, List<MemoryEntry>> memories = new ConcurrentHashMap<>();
    
    // 短时记忆（当前会话上下文）
    private final Map<String, List<MessagePair>> shortTermMemory = new ConcurrentHashMap<>();
    
    // 长时记忆（重要事件摘要）
    private final Map<String, List<String>> longTermMemory = new ConcurrentHashMap<>();

    private static final int MAX_SHORT_TERM = 20;
    private static final int MAX_LONG_TERM = 50;

    @PostConstruct
    public void init() {
        loadFromDisk();
        log.info("会话记忆初始化完成，已加载 {} 个用户的记忆", memories.size());
    }

    @PreDestroy
    public void destroy() {
        saveToDisk();
        log.info("会话记忆已持久化");
    }

    /**
     * 记录一轮对话
     */
    public void recordExchange(String userId, String userMessage, String aiResponse) {
        MessagePair pair = new MessagePair(userMessage, aiResponse, Instant.now());
        shortTermMemory.computeIfAbsent(userId, k -> new ArrayList<>()).add(pair);

        // 防止短时记忆溢出
        List<MessagePair> shortTerm = shortTermMemory.get(userId);
        if (shortTerm.size() > MAX_SHORT_TERM) {
            // 将前一半转为长时摘要
            summarizeToLongTerm(userId, shortTerm);
            // 保留最近的一半
            int keep = MAX_SHORT_TERM / 2;
            while (shortTerm.size() > keep) {
                shortTerm.remove(0);
            }
        }

        // 添加到持久化记忆
        MemoryEntry entry = new MemoryEntry();
        entry.setTimestamp(Instant.now().toString());
        entry.setUserMessage(userMessage);
        entry.setAiResponse(aiResponse.substring(0, Math.min(200, aiResponse.length())));
        entry.setSummary(generateSummary(userMessage, aiResponse));

        memories.computeIfAbsent(userId, k -> new ArrayList<>()).add(entry);
    }

    /**
     * 将短时记忆摘要存入长时记忆
     */
    private void summarizeToLongTerm(String userId, List<MessagePair> shortTerm) {
        List<String> longTerm = longTermMemory.computeIfAbsent(userId, k -> new ArrayList<>());
        
        int batchSize = Math.min(10, shortTerm.size());
        List<MessagePair> batch = shortTerm.subList(0, batchSize);
        
        StringBuilder summary = new StringBuilder("对话摘要 [");
        summary.append(batch.get(0).timestamp.toString()).append(" ~ ");
        summary.append(batch.get(batch.size() - 1).timestamp.toString()).append("]: ");
        
        Set<String> topics = new HashSet<>();
        for (MessagePair pair : batch) {
            topics.add(extractTopic(pair.userMessage));
        }
        summary.append(String.join("、", topics));
        summary.append(" 相关讨论，共 ").append(batch.size()).append(" 轮对话");
        
        longTerm.add(summary.toString());
        
        // 防止长时记忆溢出
        if (longTerm.size() > MAX_LONG_TERM) {
            longTerm.remove(0);
        }
    }

    /**
     * 提取话题关键词
     */
    private String extractTopic(String message) {
        if (message == null || message.isEmpty()) return "通用";
        
        // 简单关键词提取
        String[] keywords = {"简历", "Word", "Excel", "PPT", "面试", "学习计划", 
                             "编程", "Java", "Python", "Spring", "前端", "数据库",
                             "文档", "表格", "演示", "清洗", "合并", "搜索"};
        for (String kw : keywords) {
            if (message.contains(kw)) return kw;
        }
        
        // 返回前10个字符作为话题
        return message.length() > 10 ? message.substring(0, 10) + "..." : message;
    }

    /**
     * 生成单轮对话摘要
     */
    private String generateSummary(String userMessage, String aiResponse) {
        String topic = extractTopic(userMessage);
        String shortResponse = aiResponse != null && aiResponse.length() > 100 ? 
                aiResponse.substring(0, 100) + "..." : aiResponse;
        return String.format("[%s] %s -> %s", topic, 
                userMessage != null && userMessage.length() > 50 ? userMessage.substring(0, 50) + "..." : userMessage,
                shortResponse);
    }

    /**
     * 获取用户的对话记忆摘要（用于注入 System Prompt）
     */
    public String getMemoryContext(String userId, String currentQuery) {
        if (userId == null || userId.isEmpty()) return "";

        StringBuilder context = new StringBuilder();

        // 1. 短时记忆（最近对话）
        List<MessagePair> shortTerm = shortTermMemory.get(userId);
        if (shortTerm != null && !shortTerm.isEmpty()) {
            context.append("## 🧠 最近对话记忆\n");
            int start = Math.max(0, shortTerm.size() - 5); // 最近5轮
            for (int i = start; i < shortTerm.size(); i++) {
                MessagePair pair = shortTerm.get(i);
                context.append("- 用户: ").append(pair.userMessage)
                        .append("\n  助手: ").append(
                                pair.aiResponse.length() > 150 ? pair.aiResponse.substring(0, 150) + "..." : pair.aiResponse)
                        .append("\n");
            }
            context.append("\n");
        }

        // 2. 长时记忆（历史摘要）
        List<String> longTerm = longTermMemory.get(userId);
        if (longTerm != null && !longTerm.isEmpty()) {
            context.append("## 📜 历史记忆摘要\n");
            int start = Math.max(0, longTerm.size() - 5); // 最近5条摘要
            for (int i = start; i < longTerm.size(); i++) {
                context.append("- ").append(longTerm.get(i)).append("\n");
            }
            context.append("\n");
        }

        // 3. 搜索与当前查询相关的历史记忆
        if (currentQuery != null && !currentQuery.isEmpty()) {
            List<MemoryEntry> userMemories = memories.getOrDefault(userId, Collections.emptyList());
            String lowerQuery = currentQuery.toLowerCase();
            List<MemoryEntry> relevant = userMemories.stream()
                    .filter(m -> m.getUserMessage() != null && m.getUserMessage().toLowerCase().contains(lowerQuery))
                    .limit(3)
                    .collect(Collectors.toList());
            
            if (!relevant.isEmpty()) {
                context.append("## 🔗 相关历史记录\n");
                for (MemoryEntry m : relevant) {
                    context.append("- ").append(m.getSummary()).append("\n");
                }
                context.append("\n");
            }
        }

        return context.toString().trim();
    }

    /**
     * 获取用户偏好从记忆中推断
     */
    public Map<String, String> inferPreferences(String userId) {
        Map<String, String> inferred = new LinkedHashMap<>();
        List<MemoryEntry> userMemories = memories.getOrDefault(userId, Collections.emptyList());
        
        if (userMemories.isEmpty()) return inferred;

        // 统计话题频率
        Map<String, Long> topicFrequency = userMemories.stream()
                .map(m -> extractTopic(m.getUserMessage()))
                .collect(Collectors.groupingBy(t -> t, Collectors.counting()));

        // 按频率排序
        topicFrequency.entrySet().stream()
                .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                .limit(5)
                .forEach(e -> inferred.put("常关注话题_" + e.getKey(), e.getValue() + "次"));

        return inferred;
    }

    /**
     * 清除用户短时记忆（开始新会话时）
     */
    public void clearShortTerm(String userId) {
        shortTermMemory.remove(userId);
        log.info("已清除用户 {} 的短时记忆", userId);
    }

    /**
     * 获取记忆统计信息
     */
    public Map<String, Object> getStats(String userId) {
        Map<String, Object> stats = new LinkedHashMap<>();
        stats.put("总记忆条数", memories.getOrDefault(userId, Collections.emptyList()).size());
        stats.put("短时记忆条数", shortTermMemory.getOrDefault(userId, Collections.emptyList()).size());
        stats.put("长时摘要条数", longTermMemory.getOrDefault(userId, Collections.emptyList()).size());
        return stats;
    }

    // ==================== 持久化 ====================

    private void loadFromDisk() {
        try {
            Path path = Paths.get(memoryPath, "conversation_memory.json");
            if (!Files.exists(path)) {
                log.info("记忆文件不存在，将创建新的: {}", path);
                return;
            }
            FileReader reader = new FileReader(path.toFile());
            Type type = new TypeToken<Map<String, List<MemoryEntry>>>() {}.getType();
            Map<String, List<MemoryEntry>> loaded = gson.fromJson(reader, type);
            if (loaded != null) {
                memories.putAll(loaded);
            }
            reader.close();
        } catch (IOException e) {
            log.warn("加载记忆文件失败: {}", e.getMessage());
        }
    }

    private synchronized void saveToDisk() {
        try {
            Path dir = Paths.get(memoryPath);
            if (!Files.exists(dir)) {
                Files.createDirectories(dir);
            }
            Path path = Paths.get(memoryPath, "conversation_memory.json");
            FileWriter writer = new FileWriter(path.toFile());
            gson.toJson(memories, writer);
            writer.close();
            log.info("记忆已保存到: {}，共 {} 个用户", path, memories.size());
        } catch (IOException e) {
            log.error("保存记忆文件失败: {}", e.getMessage());
        }
    }

    // ==================== 内部类 ====================

    public static class MemoryEntry {
        private String timestamp;
        private String userMessage;
        private String aiResponse;
        private String summary;

        public String getTimestamp() { return timestamp; }
        public void setTimestamp(String timestamp) { this.timestamp = timestamp; }
        public String getUserMessage() { return userMessage; }
        public void setUserMessage(String userMessage) { this.userMessage = userMessage; }
        public String getAiResponse() { return aiResponse; }
        public void setAiResponse(String aiResponse) { this.aiResponse = aiResponse; }
        public String getSummary() { return summary; }
        public void setSummary(String summary) { this.summary = summary; }
    }

    private static class MessagePair {
        final String userMessage;
        final String aiResponse;
        final Instant timestamp;

        MessagePair(String userMessage, String aiResponse, Instant timestamp) {
            this.userMessage = userMessage;
            this.aiResponse = aiResponse;
            this.timestamp = timestamp;
        }
    }
}