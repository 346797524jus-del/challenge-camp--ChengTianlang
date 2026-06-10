package com.yupi.aicodehelper.ai.tools;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.extern.slf4j.Slf4j;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.select.Elements;

import org.springframework.stereotype.Component;

import java.io.IOException;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * 面试题搜索工具
 * 从面试鸭网站获取关键词相关的面试题列表
 */
@Slf4j
@Component
public class InterviewQuestionTool {

    private static final int MAX_RESULTS = 20;
    private static final int TIMEOUT_MS = 8000;

    /**
     * 从面试鸭网站获取关键词相关的面试题列表
     *
     * @param keyword 搜索关键词（如"redis"、"java多线程"）
     * @return 面试题列表，若失败则返回错误信息
     */
    @Tool(name = "interviewQuestionSearch", value = """
            Retrieves relevant interview questions from mianshiya.com based on a keyword.
            Use this tool when the user asks for interview questions about specific technologies,
            programming concepts, or job-related topics. The input should be a clear search term.
            """
    )
    public String searchInterviewQuestions(@P(value = "the keyword to search") String keyword) {
        // 参数校验
        if (keyword == null || keyword.trim().isEmpty()) {
            return "搜索失败: 关键词不能为空";
        }

        List<String> questions = new ArrayList<>();
        String encodedKeyword = URLEncoder.encode(keyword.trim(), StandardCharsets.UTF_8);
        String url = "https://www.mianshiya.com/search/all?searchText=" + encodedKeyword;

        Document doc;
        try {
            doc = Jsoup.connect(url)
                    .userAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                    .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
                    .header("Accept-Language", "zh-CN,zh;q=0.9,en;q=0.8")
                    .timeout(TIMEOUT_MS)
                    .get();
        } catch (IOException e) {
            log.error("搜索面试题失败: {}", e.getMessage());
            return "搜索面试题失败: " + e.getMessage() + "\n建议：请检查网络连接，或尝试使用其他关键词。";
        }

        // 提取面试题 - 尝试多种选择器
        Elements questionElements = doc.select(".ant-table-cell > a");
        if (questionElements.isEmpty()) {
            // 备选选择器
            questionElements = doc.select("a[href*=/question/]");
        }
        if (questionElements.isEmpty()) {
            // 再备选：提取所有链接文本
            questionElements = doc.select("a");
        }

        questionElements.forEach(el -> {
            String text = el.text().trim();
            if (!text.isEmpty() && questions.size() < MAX_RESULTS) {
                questions.add(text);
            }
        });

        if (questions.isEmpty()) {
            return "未找到与 \"" + keyword + "\" 相关的面试题，请尝试其他关键词。";
        }

        StringBuilder result = new StringBuilder();
        result.append("找到 ").append(questions.size()).append(" 条与 \"").append(keyword).append("\" 相关的面试题：\n\n");
        for (int i = 0; i < questions.size(); i++) {
            result.append(i + 1).append(". ").append(questions.get(i)).append("\n");
        }
        return result.toString();
    }
}
