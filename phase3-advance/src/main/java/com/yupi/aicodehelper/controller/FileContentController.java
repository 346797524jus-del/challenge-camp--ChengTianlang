package com.yupi.aicodehelper.controller;

import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.File;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 文件内容控制器 - 提供文件列表、文件内容预览（Base64）等功能
 * 让前端能够直接获取文件内容进行在线预览
 */
@RestController
@RequestMapping("/files")
public class FileContentController {

    private static final String GENERATED_DOCS_DIR = "generated-docs";

    /**
     * 获取所有已生成的文件列表
     */
    @GetMapping("/list")
    public ResponseEntity<Map<String, Object>> listFiles() {
        Map<String, Object> result = new HashMap<>();
        List<Map<String, Object>> files = new ArrayList<>();
        
        File docsDir = new File(GENERATED_DOCS_DIR);
        if (docsDir.exists() && docsDir.isDirectory()) {
            collectFiles(docsDir, files);
        }
        
        // 按修改时间排序（最新的在前）
        files.sort((a, b) -> Long.compare(
            (Long) b.getOrDefault("lastModified", 0L),
            (Long) a.getOrDefault("lastModified", 0L)
        ));
        
        result.put("files", files);
        result.put("total", files.size());
        return ResponseEntity.ok(result);
    }

    /**
     * 获取文件内容（Base64 编码），用于前端直接预览
     */
    @GetMapping("/content/{fileName}")
    public ResponseEntity<Map<String, Object>> getFileContent(@PathVariable String fileName) {
        try {
            String decodedFileName = URLDecoder.decode(fileName, StandardCharsets.UTF_8);
            File targetFile = findFile(new File(GENERATED_DOCS_DIR), decodedFileName);
            
            if (targetFile == null || !targetFile.exists()) {
                return ResponseEntity.notFound().build();
            }

            byte[] fileBytes = Files.readAllBytes(targetFile.toPath());
            String base64Content = Base64.getEncoder().encodeToString(fileBytes);
            String ext = getFileExtension(decodedFileName).toLowerCase();
            
            Map<String, Object> result = new HashMap<>();
            result.put("fileName", decodedFileName);
            result.put("content", base64Content);
            result.put("fileType", ext);
            result.put("fileSize", targetFile.length());
            result.put("lastModified", targetFile.lastModified());
            
            return ResponseEntity.ok(result);
        } catch (Exception e) {
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    /**
     * 删除指定文件
     */
    @DeleteMapping("/{fileName}")
    public ResponseEntity<Map<String, Object>> deleteFile(@PathVariable String fileName) {
        try {
            String decodedFileName = URLDecoder.decode(fileName, StandardCharsets.UTF_8);
            File targetFile = findFile(new File(GENERATED_DOCS_DIR), decodedFileName);
            
            if (targetFile != null && targetFile.exists()) {
                targetFile.delete();
                Map<String, Object> result = new HashMap<>();
                result.put("success", true);
                result.put("message", "文件已删除");
                return ResponseEntity.ok(result);
            }
            return ResponseEntity.notFound().build();
        } catch (Exception e) {
            Map<String, Object> error = new HashMap<>();
            error.put("error", e.getMessage());
            return ResponseEntity.badRequest().body(error);
        }
    }

    private void collectFiles(File dir, List<Map<String, Object>> files) {
        File[] list = dir.listFiles();
        if (list == null) return;
        
        for (File file : list) {
            if (file.isDirectory()) {
                collectFiles(file, files);
            } else {
                String name = file.getName();
                String ext = getFileExtension(name).toLowerCase();
                if (ext.equals("docx") || ext.equals("xlsx") || ext.equals("pptx")) {
                    Map<String, Object> fileInfo = new HashMap<>();
                    fileInfo.put("name", name);
                    fileInfo.put("size", file.length());
                    fileInfo.put("lastModified", file.lastModified());
                    fileInfo.put("type", ext);
                    files.add(fileInfo);
                }
            }
        }
    }

    private File findFile(File dir, String fileName) {
        if (dir == null || !dir.isDirectory()) return null;
        File[] files = dir.listFiles();
        if (files == null) return null;
        for (File file : files) {
            if (file.isDirectory()) {
                File found = findFile(file, fileName);
                if (found != null) return found;
            } else if (file.getName().equals(fileName)) {
                return file;
            }
        }
        return null;
    }

    private String getFileExtension(String fileName) {
        int dotIndex = fileName.lastIndexOf('.');
        return dotIndex > 0 ? fileName.substring(dotIndex + 1) : "";
    }
}
