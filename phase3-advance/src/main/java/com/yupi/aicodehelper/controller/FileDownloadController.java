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

/**
 * 文件下载控制器 - 提供生成文件的下载和预览服务
 */
@RestController
@RequestMapping("/files")
public class FileDownloadController {

    /** 生成文件的根目录 */
    private static final String GENERATED_DOCS_DIR = "generated-docs";

    /**
     * 下载生成的文件
     * @param fileName 文件名
     * @return 文件资源
     */
    @GetMapping("/{fileName}")
    public ResponseEntity<Resource> downloadFile(@PathVariable String fileName) {
        try {
            // 解码文件名
            String decodedFileName = URLDecoder.decode(fileName, StandardCharsets.UTF_8);
            
            // 在所有子目录中查找文件
            File docsDir = new File(GENERATED_DOCS_DIR);
            File targetFile = findFile(docsDir, decodedFileName);
            
            if (targetFile == null || !targetFile.exists()) {
                // 尝试直接使用文件名查找（兼容不同路径格式）
                Path directPath = Paths.get(GENERATED_DOCS_DIR, decodedFileName);
                if (Files.exists(directPath)) {
                    targetFile = directPath.toFile();
                } else {
                    // 尝试在子目录中查找
                    File[] subDirs = docsDir.listFiles(File::isDirectory);
                    if (subDirs != null) {
                        for (File subDir : subDirs) {
                            File subFile = new File(subDir, decodedFileName);
                            if (subFile.exists()) {
                                targetFile = subFile;
                                break;
                            }
                        }
                    }
                }
            }
            
            if (targetFile == null || !targetFile.exists()) {
                return ResponseEntity.notFound().build();
            }

            Resource resource = new FileSystemResource(targetFile);
            
            // 根据文件扩展名设置 Content-Type
            MediaType mediaType = getMediaType(decodedFileName);
            
            return ResponseEntity.ok()
                    .contentType(mediaType)
                    .contentLength(targetFile.length())
                    .header(HttpHeaders.CONTENT_DISPOSITION, 
                            "attachment; filename=\"" + new String(decodedFileName.getBytes(StandardCharsets.UTF_8), StandardCharsets.ISO_8859_1) + "\"")
                    .body(resource);
        } catch (Exception e) {
            return ResponseEntity.badRequest().build();
        }
    }

    /**
     * 在目录中递归查找文件
     */
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

    /**
     * 根据文件扩展名获取 MediaType
     */
    private MediaType getMediaType(String fileName) {
        if (fileName.endsWith(".docx")) {
            return MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.wordprocessingml.document");
        } else if (fileName.endsWith(".xlsx")) {
            return MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
        } else if (fileName.endsWith(".pptx")) {
            return MediaType.parseMediaType("application/vnd.openxmlformats-officedocument.presentationml.presentation");
        } else {
            return MediaType.APPLICATION_OCTET_STREAM;
        }
    }
}
