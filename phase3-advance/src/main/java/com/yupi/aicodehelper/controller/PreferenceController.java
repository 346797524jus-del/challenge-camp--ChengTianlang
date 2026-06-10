package com.yupi.aicodehelper.controller;

import com.yupi.aicodehelper.ai.rag.DataLoader;
import com.yupi.aicodehelper.ai.memory.ConversationMemory;
import jakarta.annotation.Resource;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * 偏好管理控制器 - 提供用户偏好的 CRUD API
 * 
 * 功能：
 * - 获取用户偏好列表
 * - 获取/设置特定偏好值
 * - 删除偏好
 * - 获取系统默认偏好
 */
@Slf4j
@RestController
@RequestMapping("/preferences")
public class PreferenceController {

    @Resource
    private DataLoader dataLoader;

    @Resource
    private ConversationMemory conversationMemory;

    /**
     * 获取指定用户的所有偏好
     */
    @GetMapping("/{userId}")
    public Map<String, Object> getUserPreferences(@PathVariable String userId) {
        Map<String, Object> result = new LinkedHashMap<>();
        
        // 1. 从 DataLoader 获取预设偏好
        List<DataLoader.PreferenceEntry> savedPrefs = dataLoader.getUserPreferences(userId);
        List<Map<String, String>> prefList = new ArrayList<>();
        for (DataLoader.PreferenceEntry p : savedPrefs) {
            Map<String, String> item = new LinkedHashMap<>();
            item.put("key", p.getPrefKey());
            item.put("value", p.getPrefValue());
            item.put("category", p.getPreferenceCategory());
            item.put("note", p.getNote());
            item.put("version", p.getVersion());
            prefList.add(item);
        }
        result.put("savedPreferences", prefList);

        // 2. 从 ConversationMemory 推断偏好
        Map<String, String> inferred = conversationMemory.inferPreferences(userId);
        result.put("inferredPreferences", inferred);

        // 3. 系统默认偏好
        List<DataLoader.PreferenceEntry> allPrefs = dataLoader.getAllPreferences();
        List<Map<String, String>> defaultList = new ArrayList<>();
        for (DataLoader.PreferenceEntry p : allPrefs) {
            if ("SYSTEM_DEFAULT".equals(p.getUid())) {
                Map<String, String> item = new LinkedHashMap<>();
                item.put("key", p.getPrefKey());
                item.put("value", p.getPrefValue());
                item.put("category", p.getPreferenceCategory());
                defaultList.add(item);
            }
        }
        result.put("systemDefaults", defaultList);

        return result;
    }

    /**
     * 获取特定偏好值
     */
    @GetMapping("/{userId}/value")
    public Map<String, Object> getPreferenceValue(
            @PathVariable String userId,
            @RequestParam String key) {
        String value = dataLoader.getPreferenceValue(userId, key);
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("userId", userId);
        result.put("key", key);
        result.put("value", value != null ? value : "未设置");
        result.put("found", value != null);
        return result;
    }

    /**
     * 获取所有偏好（管理员视图）
     */
    @GetMapping("/all")
    public Map<String, Object> getAllPreferences() {
        List<DataLoader.PreferenceEntry> all = dataLoader.getAllPreferences();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("total", all.size());
        
        // 按用户分组
        Map<String, List<Map<String, String>>> grouped = new LinkedHashMap<>();
        for (DataLoader.PreferenceEntry p : all) {
            String uid = p.getUid() != null ? p.getUid() : "未知";
            grouped.computeIfAbsent(uid, k -> new ArrayList<>()).add(Map.of(
                    "key", p.getPrefKey() != null ? p.getPrefKey() : "",
                    "value", p.getPrefValue() != null ? p.getPrefValue() : "",
                    "category", p.getPreferenceCategory() != null ? p.getPreferenceCategory() : "",
                    "version", p.getVersion() != null ? p.getVersion() : ""
            ));
        }
        result.put("byUser", grouped);
        
        return result;
    }

    /**
     * 获取全局配置摘要
     */
    @GetMapping("/context")
    public Map<String, Object> getSystemContext() {
        String context = dataLoader.getSystemContext();
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("systemContext", context);
        result.put("isEmpty", context == null || context.isEmpty());
        return result;
    }
}