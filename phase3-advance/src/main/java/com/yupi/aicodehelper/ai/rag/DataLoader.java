package com.yupi.aicodehelper.ai.rag;

import com.google.gson.Gson;
import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.reflect.TypeToken;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.io.FileReader;
import java.io.IOException;
import java.lang.reflect.Type;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * 数据加载器 - 加载 phase2-consolidata 清洗后的数据
 * 提供知识库、偏好、聊天记录和工具结果的检索能力
 */
@Slf4j
@Component
public class DataLoader {

    private final Gson gson = new Gson();

    @Value("${data.phase2.path:../phase2-consolidata}")
    private String phase2DataPath;

    // 内存数据存储
    private List<KnowledgeEntry> knowledgeBase = new ArrayList<>();
    private List<PreferenceEntry> preferences = new ArrayList<>();
    private List<ChatLogEntry> chatLogs = new ArrayList<>();
    private List<ToolResultEntry> toolResults = new ArrayList<>();

    // 全局配置
    private Map<String, Object> globalConfig = new HashMap<>();

    @PostConstruct
    public void init() {
        loadAllData();
    }

    /**
     * 加载所有 phase2 数据
     */
    public void loadAllData() {
        loadKnowledgeBase();
        loadPreferences();
        loadChatLogs();
        loadToolResults();
        log.info("数据加载完成: 知识库={}条, 偏好={}条, 聊天记录={}条, 工具结果={}条",
                knowledgeBase.size(), preferences.size(), chatLogs.size(), toolResults.size());
    }

    /**
     * 加载知识库
     */
    private void loadKnowledgeBase() {
        Path path = Paths.get(phase2DataPath, "knowledge.json");
        if (!Files.exists(path)) {
            log.warn("知识库文件不存在: {}", path);
            return;
        }
        try (FileReader reader = new FileReader(path.toFile())) {
            Type listType = new TypeToken<List<KnowledgeEntry>>() {}.getType();
            knowledgeBase = gson.fromJson(reader, listType);
            log.info("加载知识库: {} 条", knowledgeBase.size());
        } catch (IOException e) {
            log.error("加载知识库失败: {}", e.getMessage());
        }
    }

    /**
     * 加载偏好配置
     */
    private void loadPreferences() {
        Path path = Paths.get(phase2DataPath, "preferences.json");
        if (!Files.exists(path)) {
            log.warn("偏好文件不存在: {}", path);
            return;
        }
        try (FileReader reader = new FileReader(path.toFile())) {
            JsonObject json = gson.fromJson(reader, JsonObject.class);
            if (json.has("global_config")) {
                globalConfig = gson.fromJson(json.get("global_config"), Map.class);
            }
            if (json.has("user_preferences")) {
                JsonArray arr = json.getAsJsonArray("user_preferences");
                Type listType = new TypeToken<List<PreferenceEntry>>() {}.getType();
                preferences = gson.fromJson(arr, listType);
            }
            log.info("加载偏好: {} 条", preferences.size());
        } catch (IOException e) {
            log.error("加载偏好失败: {}", e.getMessage());
        }
    }

    /**
     * 加载聊天记录
     */
    private void loadChatLogs() {
        Path path = Paths.get(phase2DataPath, "chat_logs.json");
        if (!Files.exists(path)) {
            log.warn("聊天记录文件不存在: {}", path);
            return;
        }
        try (FileReader reader = new FileReader(path.toFile())) {
            Type listType = new TypeToken<List<ChatLogEntry>>() {}.getType();
            chatLogs = gson.fromJson(reader, listType);
            log.info("加载聊天记录: {} 条", chatLogs.size());
        } catch (IOException e) {
            log.error("加载聊天记录失败: {}", e.getMessage());
        }
    }

    /**
     * 加载工具结果
     */
    private void loadToolResults() {
        Path path = Paths.get(phase2DataPath, "tool_results.json");
        if (!Files.exists(path)) {
            log.warn("工具结果文件不存在: {}", path);
            return;
        }
        try (FileReader reader = new FileReader(path.toFile())) {
            Type listType = new TypeToken<List<ToolResultEntry>>() {}.getType();
            toolResults = gson.fromJson(reader, listType);
            log.info("加载工具结果: {} 条", toolResults.size());
        } catch (IOException e) {
            log.error("加载工具结果失败: {}", e.getMessage());
        }
    }

    // ==================== 检索方法 ====================

    /**
     * 搜索知识库 - 基于关键词匹配
     */
    public List<KnowledgeEntry> searchKnowledge(String query, int maxResults) {
        if (query == null || query.trim().isEmpty()) return Collections.emptyList();
        
        String lowerQuery = query.toLowerCase();
        List<ScoredEntry<KnowledgeEntry>> scored = new ArrayList<>();

        for (KnowledgeEntry entry : knowledgeBase) {
            double score = 0;
            
            // 标题匹配（权重最高）
            if (entry.getTitle() != null && entry.getTitle().toLowerCase().contains(lowerQuery)) {
                score += 10;
            }
            // 标签匹配
            if (entry.getTags() != null) {
                for (String tag : entry.getTags()) {
                    if (tag.toLowerCase().contains(lowerQuery)) {
                        score += 5;
                    }
                }
            }
            // 内容匹配
            if (entry.getBodySteps() != null && entry.getBodySteps().toLowerCase().contains(lowerQuery)) {
                score += 3;
            }

            if (score > 0) {
                scored.add(new ScoredEntry<>(entry, score));
            }
        }

        // 按分数排序
        scored.sort((a, b) -> Double.compare(b.score, a.score));
        return scored.stream()
                .limit(maxResults)
                .map(e -> e.entry)
                .collect(Collectors.toList());
    }

    /**
     * 获取用户偏好 - 按用户ID和偏好键
     */
    public List<PreferenceEntry> getUserPreferences(String uid) {
        if (uid == null) return Collections.emptyList();
        return preferences.stream()
                .filter(p -> uid.equals(p.getUid()))
                .collect(Collectors.toList());
    }

    /**
     * 获取所有偏好（含系统默认）
     */
    public List<PreferenceEntry> getAllPreferences() {
        return new ArrayList<>(preferences);
    }

    /**
     * 获取特定偏好键的值（按版本优先级）
     */
    public String getPreferenceValue(String uid, String prefKey) {
        // 先找用户特定偏好
        List<PreferenceEntry> userPrefs = preferences.stream()
                .filter(p -> uid.equals(p.getUid()) && prefKey.equals(p.getPrefKey()))
                .sorted((a, b) -> b.getVersion().compareTo(a.getVersion())) // 最新版本优先
                .collect(Collectors.toList());

        if (!userPrefs.isEmpty()) {
            // 排除 temporary 类型（临时偏好）
            for (PreferenceEntry p : userPrefs) {
                if (!"temporary".equals(p.getPreferenceCategory())) {
                    return p.getPrefValue();
                }
            }
        }

        // 找系统默认
        List<PreferenceEntry> defaults = preferences.stream()
                .filter(p -> "SYSTEM_DEFAULT".equals(p.getUid()) && prefKey.equals(p.getPrefKey()))
                .collect(Collectors.toList());
        if (!defaults.isEmpty()) {
            return defaults.get(0).getPrefValue();
        }

        return null;
    }

    /**
     * 搜索聊天记录
     */
    public List<ChatLogEntry> searchChatLogs(String query, int maxResults) {
        if (query == null || query.trim().isEmpty()) return Collections.emptyList();
        
        String lowerQuery = query.toLowerCase();
        List<ScoredEntry<ChatLogEntry>> scored = new ArrayList<>();

        for (ChatLogEntry entry : chatLogs) {
            double score = 0;
            if (entry.getText() != null && entry.getText().toLowerCase().contains(lowerQuery)) {
                score += entry.getText().length() > 50 ? 5 : 3;
            }
            if (entry.getSession() != null && entry.getSession().toLowerCase().contains(lowerQuery)) {
                score += 2;
            }
            if (score > 0) {
                scored.add(new ScoredEntry<>(entry, score));
            }
        }

        scored.sort((a, b) -> Double.compare(b.score, a.score));
        return scored.stream()
                .limit(maxResults)
                .map(e -> e.entry)
                .collect(Collectors.toList());
    }

    /**
     * 搜索工具结果
     */
    public List<ToolResultEntry> searchToolResults(String query, int maxResults) {
        if (query == null || query.trim().isEmpty()) return Collections.emptyList();
        
        String lowerQuery = query.toLowerCase();
        List<ScoredEntry<ToolResultEntry>> scored = new ArrayList<>();

        for (ToolResultEntry entry : toolResults) {
            double score = 0;
            if (entry.getTool() != null && entry.getTool().toLowerCase().contains(lowerQuery)) {
                score += 5;
            }
            if (entry.getRawOutput() != null && entry.getRawOutput().toLowerCase().contains(lowerQuery)) {
                score += 3;
            }
            if (score > 0) {
                scored.add(new ScoredEntry<>(entry, score));
            }
        }

        scored.sort((a, b) -> Double.compare(b.score, a.score));
        return scored.stream()
                .limit(maxResults)
                .map(e -> e.entry)
                .collect(Collectors.toList());
    }

    /**
     * 综合检索 - 从所有数据源检索相关信息
     */
    public String comprehensiveSearch(String query, int maxResults) {
        StringBuilder result = new StringBuilder();
        
        // 1. 知识库检索
        List<KnowledgeEntry> knowledgeResults = searchKnowledge(query, maxResults);
        if (!knowledgeResults.isEmpty()) {
            result.append("【知识库匹配结果】\n");
            for (KnowledgeEntry entry : knowledgeResults) {
                result.append("- ").append(entry.getTitle()).append("\n");
                if (entry.getBodySteps() != null && !entry.getBodySteps().isEmpty()) {
                    result.append("  ").append(entry.getBodySteps().substring(0, Math.min(200, entry.getBodySteps().length()))).append("\n");
                }
            }
            result.append("\n");
        }

        // 2. 偏好检索
        List<PreferenceEntry> prefResults = preferences.stream()
                .filter(p -> {
                    if (p.getPrefKey() != null && p.getPrefKey().toLowerCase().contains(query.toLowerCase())) return true;
                    if (p.getPrefValue() != null && p.getPrefValue().toLowerCase().contains(query.toLowerCase())) return true;
                    return false;
                })
                .limit(maxResults)
                .collect(Collectors.toList());
        if (!prefResults.isEmpty()) {
            result.append("【偏好匹配结果】\n");
            for (PreferenceEntry entry : prefResults) {
                result.append("- [").append(entry.getUid()).append("] ")
                      .append(entry.getPrefKey()).append(": ").append(entry.getPrefValue())
                      .append(" (").append(entry.getPreferenceCategory()).append(")\n");
            }
            result.append("\n");
        }

        // 3. 聊天记录检索
        List<ChatLogEntry> chatResults = searchChatLogs(query, maxResults);
        if (!chatResults.isEmpty()) {
            result.append("【历史对话匹配结果】\n");
            for (ChatLogEntry entry : chatResults) {
                result.append("- [").append(entry.getSession()).append("] ")
                      .append(entry.getRole()).append(": ")
                      .append(entry.getText().substring(0, Math.min(100, entry.getText().length()))).append("\n");
            }
            result.append("\n");
        }

        // 4. 工具结果检索
        List<ToolResultEntry> toolResults = searchToolResults(query, maxResults);
        if (!toolResults.isEmpty()) {
            result.append("【工具执行历史匹配结果】\n");
            for (ToolResultEntry entry : toolResults) {
                result.append("- ").append(entry.getTool()).append(" [").append(entry.getStatus()).append("]: ")
                      .append(entry.getRawOutput().substring(0, Math.min(100, entry.getRawOutput().length()))).append("\n");
            }
            result.append("\n");
        }

        return result.toString().trim();
    }

    /**
     * 获取格式化后的系统提示上下文
     */
    public String getSystemContext() {
        StringBuilder context = new StringBuilder();
        
        // 全局配置
        if (!globalConfig.isEmpty()) {
            context.append("## 全局配置\n");
            if (globalConfig.containsKey("preferences_defaults")) {
                Map<String, Object> defaults = (Map<String, Object>) globalConfig.get("preferences_defaults");
                context.append("默认输出风格: ").append(defaults.getOrDefault("output_style", "未设置")).append("\n");
                context.append("Emoji策略: ").append(defaults.getOrDefault("emoji_policy", "未设置")).append("\n");
            }
            context.append("\n");
        }

        // 所有偏好摘要
        if (!preferences.isEmpty()) {
            context.append("## 用户偏好摘要\n");
            Map<String, List<PreferenceEntry>> grouped = preferences.stream()
                    .collect(Collectors.groupingBy(PreferenceEntry::getUid));
            for (Map.Entry<String, List<PreferenceEntry>> group : grouped.entrySet()) {
                context.append("用户 ").append(group.getKey()).append(":\n");
                for (PreferenceEntry p : group.getValue()) {
                    context.append("  - ").append(p.getPrefKey()).append(": ").append(p.getPrefValue());
                    if (!"explicit".equals(p.getPreferenceCategory())) {
                        context.append(" [").append(p.getPreferenceCategory()).append("]");
                    }
                    context.append("\n");
                }
            }
            context.append("\n");
        }

        return context.toString().trim();
    }

    // ==================== 内部类 ====================

    public static class KnowledgeEntry {
        private String title;
        private List<String> tags;
        private String body_steps;

        public String getTitle() { return title; }
        public List<String> getTags() { return tags; }
        public String getBodySteps() { return body_steps; }
    }

    public static class PreferenceEntry {
        private String pref_id;
        private String uid;
        private String pref_key;
        private String pref_value;
        private String version;
        private String note;
        private String preference_category;
        private String conflict_evidence;
        private String preference;

        public String getPrefId() { return pref_id; }
        public String getUid() { return uid; }
        public String getPrefKey() { return pref_key; }
        public String getPrefValue() { return pref_value; }
        public String getVersion() { return version; }
        public String getNote() { return note; }
        public String getPreferenceCategory() { return preference_category; }
        public String getConflictEvidence() { return conflict_evidence; }
        public String getPreference() { return preference; }
    }

    public static class ChatLogEntry {
        private String session;
        private String uid;
        private String role;
        private String text;
        private String ts;
        private List<String> flags;

        public String getSession() { return session; }
        public String getUid() { return uid; }
        public String getRole() { return role; }
        public String getText() { return text; }
        public String getTs() { return ts; }
        public List<String> getFlags() { return flags; }
    }

    public static class ToolResultEntry {
        private String trace;
        private String tool;
        private String status;
        private String raw_output;
        private double exec_ms;
        private String trace_id;
        private String tool_name;
        private double duration;

        public String getTrace() { return trace; }
        public String getTool() { return tool; }
        public String getStatus() { return status; }
        public String getRawOutput() { return raw_output; }
        public double getExecMs() { return exec_ms; }
        public String getTraceId() { return trace_id; }
        public String getToolName() { return tool_name; }
        public double getDuration() { return duration; }
    }

    private static class ScoredEntry<T> {
        final T entry;
        final double score;
        ScoredEntry(T entry, double score) {
            this.entry = entry;
            this.score = score;
        }
    }
}
