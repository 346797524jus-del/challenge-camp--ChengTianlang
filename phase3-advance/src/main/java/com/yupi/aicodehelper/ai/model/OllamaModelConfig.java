package com.yupi.aicodehelper.ai.model;

import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.StreamingChatModel;
import dev.langchain4j.model.chat.listener.ChatModelListener;
import dev.langchain4j.model.openai.OpenAiChatModel;
import dev.langchain4j.model.openai.OpenAiStreamingChatModel;
import jakarta.annotation.Resource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.Duration;
import java.util.List;

@Configuration
public class OllamaModelConfig {

    @Value("${langchain4j.open-ai.chat-model.base-url}")
    private String baseUrl;

    @Value("${langchain4j.open-ai.chat-model.model-name}")
    private String modelName;

    @Value("${langchain4j.open-ai.chat-model.api-key}")
    private String apiKey;

    @Resource
    private ChatModelListener chatModelListener;

    @Bean
    public ChatModel ollamaChatModel() {
        // 去除可能的空白字符（如 \r 等）
        String cleanBaseUrl = baseUrl != null ? baseUrl.trim() : "";
        String cleanModelName = modelName != null ? modelName.trim() : "";
        String cleanApiKey = apiKey != null ? apiKey.trim() : "";
        
        // 确保 baseUrl 末尾没有斜杠，然后拼接 /v1
        String apiUrl = cleanBaseUrl.endsWith("/") ? cleanBaseUrl + "v1" : cleanBaseUrl + "/v1";
        
        System.out.println("=== OllamaModelConfig ===");
        System.out.println("baseUrl: '" + cleanBaseUrl + "'");
        System.out.println("apiUrl: '" + apiUrl + "'");
        System.out.println("modelName: '" + cleanModelName + "'");
        System.out.println("apiKey: '" + cleanApiKey.substring(0, Math.min(8, cleanApiKey.length())) + "...'");
        System.out.println("=========================");
        
        return OpenAiChatModel.builder()
                .baseUrl(apiUrl)
                .apiKey(cleanApiKey)
                .modelName(cleanModelName)
                .timeout(Duration.ofMinutes(2))
                .listeners(List.of(chatModelListener))
                .maxRetries(3)
                .build();
    }

    @Bean
    public StreamingChatModel ollamaStreamingChatModel() {
        // 去除可能的空白字符
        String cleanBaseUrl = baseUrl != null ? baseUrl.trim() : "";
        String cleanModelName = modelName != null ? modelName.trim() : "";
        String cleanApiKey = apiKey != null ? apiKey.trim() : "";
        
        // 确保 baseUrl 末尾没有斜杠，然后拼接 /v1
        String apiUrl = cleanBaseUrl.endsWith("/") ? cleanBaseUrl + "v1" : cleanBaseUrl + "/v1";
        
        return OpenAiStreamingChatModel.builder()
                .baseUrl(apiUrl)
                .apiKey(cleanApiKey)
                .modelName(cleanModelName)
                .timeout(Duration.ofMinutes(2))
                .listeners(List.of(chatModelListener))
                .build();
    }
}
