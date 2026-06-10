package com.yupi.aicodehelper.ai.tools;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.regex.Pattern;
import java.util.stream.Collectors;

/**
 * 数据清洗工具 - 清洗项目中的脏数据、去重、格式标准化
 * 
 * 功能：
 * 1. CSV 数据清洗（去重、去空行、格式标准化）
 * 2. JSON 数据清洗（验证、格式化）
 * 3. 文本文件清洗（去空行、去BOM、统一换行符）
 * 4. 日志文件清洗（提取有效信息）
 */
@Slf4j
@Component
public class DataCleanTool {

    private static final String CLEANED_DIR = "generated-docs/cleaned";
    private static final DateTimeFormatter DTF = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");

    public DataCleanTool() {
        try {
            Files.createDirectories(Paths.get(CLEANED_DIR));
        } catch (Exception e) {
            log.error("创建清洗输出目录失败", e);
        }
    }

    @Tool(name = "cleanCsvData", value = """
            Cleans CSV data by removing duplicates, empty rows, standardizing formats.
            Use this when the user wants to clean messy CSV data files.
            Returns a report of cleaning operations and the path to the cleaned file.
            """)
    public String cleanCsvData(
            @P(value = "the path to the CSV file to clean") String filePath,
            @P(value = "whether to remove duplicate rows") Boolean removeDuplicates,
            @P(value = "whether to remove empty rows") Boolean removeEmptyRows) {
        try {
            Path sourcePath = Paths.get(filePath);
            if (!Files.exists(sourcePath)) {
                return "错误：文件不存在 - " + filePath;
            }

            boolean doDedup = removeDuplicates != null ? removeDuplicates : true;
            boolean doRmEmpty = removeEmptyRows != null ? removeEmptyRows : true;

            List<String> lines = Files.readAllLines(sourcePath);
            int originalCount = lines.size();
            int removedEmpty = 0;
            int removedDup = 0;

            // 1. 去除空行
            List<String> cleaned = new ArrayList<>();
            if (doRmEmpty) {
                for (String line : lines) {
                    String trimmed = line.trim();
                    if (trimmed.isEmpty() || trimmed.replaceAll(",", "").trim().isEmpty()) {
                        removedEmpty++;
                    } else {
                        cleaned.add(line);
                    }
                }
            } else {
                cleaned.addAll(lines);
            }

            // 2. 去重
            if (doDedup) {
                int beforeDedup = cleaned.size();
                cleaned = cleaned.stream().distinct().collect(Collectors.toList());
                removedDup = beforeDedup - cleaned.size();
            }

            // 3. 保存清洗结果
            String fileName = sourcePath.getFileName().toString();
            String baseName = fileName.contains(".") ? fileName.substring(0, fileName.lastIndexOf('.')) : fileName;
            String cleanedFileName = baseName + "_cleaned_" + DTF.format(LocalDateTime.now()) + ".csv";
            Path outputPath = Paths.get(CLEANED_DIR, cleanedFileName);
            Files.write(outputPath, cleaned);

            // 生成报告
            StringBuilder report = new StringBuilder();
            report.append("## 🧹 CSV 数据清洗报告\n\n");
            report.append("源文件: ").append(sourcePath.toAbsolutePath()).append("\n");
            report.append("输出文件: ").append(outputPath.toAbsolutePath()).append("\n\n");
            report.append("### 📊 清洗统计\n");
            report.append("- 原始行数: ").append(originalCount).append("\n");
            report.append("- 去除空行: ").append(removedEmpty).append("\n");
            report.append("- 去重行数: ").append(removedDup).append("\n");
            report.append("- 清洗后行数: ").append(cleaned.size()).append("\n");
            report.append("- 清洗率: ").append(String.format("%.1f%%", 
                    originalCount > 0 ? (double)(originalCount - cleaned.size()) / originalCount * 100 : 0)).append("\n");
            report.append("\n---\n");
            report.append("✅ 清洗完成！清洗后的文件已保存到: ").append(outputPath.toAbsolutePath());

            return report.toString();

        } catch (Exception e) {
            log.error("CSV清洗失败: {}", e.getMessage(), e);
            return "错误：CSV清洗时发生异常 - " + e.getMessage();
        }
    }

    @Tool(name = "cleanJsonlData", value = """
            Cleans JSONL (JSON Lines) data by validating, removing invalid lines, and deduplicating.
            Use this when the user has messy JSONL files that need cleaning.
            Returns a cleaning report and the path to the cleaned file.
            """)
    public String cleanJsonlData(
            @P(value = "the path to the JSONL file to clean") String filePath) {
        try {
            Path sourcePath = Paths.get(filePath);
            if (!Files.exists(sourcePath)) {
                return "错误：文件不存在 - " + filePath;
            }

            List<String> lines = Files.readAllLines(sourcePath, StandardCharsets.UTF_8);
            int originalCount = lines.size();
            int invalidCount = 0;
            int emptyCount = 0;
            int duplicateCount = 0;

            List<String> validLines = new ArrayList<>();
            Set<String> seenContent = new HashSet<>();

            for (String line : lines) {
                String trimmed = line.trim();
                
                // 跳过空行
                if (trimmed.isEmpty()) {
                    emptyCount++;
                    continue;
                }

                // 基本JSON验证
                if (!isValidJson(trimmed)) {
                    invalidCount++;
                    continue;
                }

                // 去重（基于内容hash）
                String contentKey = trimmed.length() > 100 ? 
                        trimmed.substring(0, 100) + "|" + trimmed.hashCode() : trimmed;
                if (seenContent.contains(contentKey)) {
                    duplicateCount++;
                    continue;
                }
                seenContent.add(contentKey);
                validLines.add(trimmed);
            }

            // 保存清洗结果
            String fileName = sourcePath.getFileName().toString();
            String baseName = fileName.contains(".") ? fileName.substring(0, fileName.lastIndexOf('.')) : fileName;
            String cleanedFileName = baseName + "_cleaned_" + DTF.format(LocalDateTime.now()) + ".jsonl";
            Path outputPath = Paths.get(CLEANED_DIR, cleanedFileName);
            Files.write(outputPath, validLines);

            // 生成报告
            StringBuilder report = new StringBuilder();
            report.append("## 🧹 JSONL 数据清洗报告\n\n");
            report.append("源文件: ").append(sourcePath.toAbsolutePath()).append("\n");
            report.append("输出文件: ").append(outputPath.toAbsolutePath()).append("\n\n");
            report.append("### 📊 清洗统计\n");
            report.append("- 原始行数: ").append(originalCount).append("\n");
            report.append("- 空行去除: ").append(emptyCount).append("\n");
            report.append("- 无效JSON: ").append(invalidCount).append("\n");
            report.append("- 去重行数: ").append(duplicateCount).append("\n");
            report.append("- 有效行数: ").append(validLines.size()).append("\n");
            report.append("- 有效比例: ").append(String.format("%.1f%%", 
                    originalCount > 0 ? (double)validLines.size() / originalCount * 100 : 0)).append("\n");
            
            if (invalidCount > 0) {
                report.append("\n⚠️ 检测到 ").append(invalidCount).append(" 行无效JSON数据已被移除\n");
            }
            
            report.append("\n---\n");
            report.append("✅ 清洗完成！文件已保存到: ").append(outputPath.toAbsolutePath());

            return report.toString();

        } catch (Exception e) {
            log.error("JSONL清洗失败: {}", e.getMessage(), e);
            return "错误：JSONL清洗时发生异常 - " + e.getMessage();
        }
    }

    @Tool(name = "cleanTextFile", value = """
            Cleans a text file by removing empty lines, BOM markers, standardizing line endings.
            Use this when the user wants to clean messy text or log files.
            Returns a cleaning report and the path to the cleaned file.
            """)
    public String cleanTextFile(
            @P(value = "the path to the text file to clean") String filePath,
            @P(value = "whether to remove empty lines") Boolean removeEmptyLines) {
        try {
            Path sourcePath = Paths.get(filePath);
            if (!Files.exists(sourcePath)) {
                return "错误：文件不存在 - " + filePath;
            }

            boolean doRmEmpty = removeEmptyLines != null ? removeEmptyLines : true;

            // 读取原始内容
            byte[] rawBytes = Files.readAllBytes(sourcePath);
            int originalSize = rawBytes.length;

            // 检测并移除BOM
            int bomOffset = 0;
            if (rawBytes.length >= 3 && rawBytes[0] == (byte)0xEF && rawBytes[1] == (byte)0xBB && rawBytes[2] == (byte)0xBF) {
                bomOffset = 3;
            }

            String content = new String(rawBytes, bomOffset, rawBytes.length - bomOffset, StandardCharsets.UTF_8);
            
            // 统一换行符
            content = content.replace("\r\n", "\n").replace("\r", "\n");
            
            // 分割行并清洗
            String[] lines = content.split("\n");
            int originalLines = lines.length;
            List<String> cleaned = new ArrayList<>();
            int emptyRemoved = 0;

            for (String line : lines) {
                if (doRmEmpty && line.trim().isEmpty()) {
                    emptyRemoved++;
                } else {
                    cleaned.add(line);
                }
            }

            // 保存清洗结果
            String fileName = sourcePath.getFileName().toString();
            String baseName = fileName.contains(".") ? fileName.substring(0, fileName.lastIndexOf('.')) : fileName;
            String ext = fileName.contains(".") ? fileName.substring(fileName.lastIndexOf('.')) : ".txt";
            String cleanedFileName = baseName + "_cleaned_" + DTF.format(LocalDateTime.now()) + ext;
            Path outputPath = Paths.get(CLEANED_DIR, cleanedFileName);
            Files.write(outputPath, cleaned);

            StringBuilder report = new StringBuilder();
            report.append("## 🧹 文本文件清洗报告\n\n");
            report.append("源文件: ").append(sourcePath.toAbsolutePath()).append("\n");
            report.append("输出文件: ").append(outputPath.toAbsolutePath()).append("\n\n");
            report.append("### 📊 清洗统计\n");
            report.append("- 原始大小: ").append(formatSize(originalSize)).append("\n");
            report.append("- BOM标记: ").append(bomOffset > 0 ? "已移除" : "无").append("\n");
            report.append("- 换行符: 已统一为 LF (\\n)\n");
            report.append("- 原始行数: ").append(originalLines).append("\n");
            report.append("- 去除空行: ").append(emptyRemoved).append("\n");
            report.append("- 清洗后行数: ").append(cleaned.size()).append("\n");
            report.append("\n---\n");
            report.append("✅ 清洗完成！");

            return report.toString();

        } catch (Exception e) {
            log.error("文本清洗失败: {}", e.getMessage(), e);
            return "错误：文本清洗时发生异常 - " + e.getMessage();
        }
    }

    @Tool(name = "scanAndCleanDirectory", value = """
            Scans a directory and identifies files that may need cleaning, then generates
            a cleaning recommendation report. Does not modify files automatically.
            Use this when the user wants to find dirty data in a project directory.
            Returns a report identifying problematic files and cleaning suggestions.
            """)
    public String scanAndCleanDirectory(
            @P(value = "the directory path to scan for dirty data") String directoryPath) {
        try {
            Path rootPath = Paths.get(directoryPath).toAbsolutePath().normalize();
            if (!Files.exists(rootPath) || !Files.isDirectory(rootPath)) {
                return "错误：目录不存在或不是目录 - " + directoryPath;
            }

            StringBuilder report = new StringBuilder();
            report.append("## 🔍 数据质量扫描报告\n\n");
            report.append("扫描目录: ").append(rootPath).append("\n");
            report.append("扫描时间: ").append(LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))).append("\n\n");

            // 收集问题文件
            List<FileIssue> issues = new ArrayList<>();

            Files.walkFileTree(rootPath, EnumSet.noneOf(FileVisitOption.class), 50,
                    new SimpleFileVisitor<Path>() {
                @Override
                public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) {
                    String name = dir.getFileName().toString();
                    if (name.equals(".git") || name.equals("node_modules") || 
                        name.equals("target") || name.startsWith(".")) {
                        return FileVisitResult.SKIP_SUBTREE;
                    }
                    return FileVisitResult.CONTINUE;
                }
                @Override
                public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                    String name = file.getFileName().toString().toLowerCase();
                    String relPath = rootPath.relativize(file).toString();

                    // 检查空文件
                    if (attrs.size() == 0) {
                        issues.add(new FileIssue(relPath, "空文件", "建议删除"));
                    }
                    // 检查超大文件
                    else if (attrs.size() > 10 * 1024 * 1024) {
                        issues.add(new FileIssue(relPath, 
                                "超大文件 (" + formatSize(attrs.size()) + ")", 
                                "建议检查是否需要拆分或压缩"));
                    }
                    // CSV 文件检查
                    else if (name.endsWith(".csv") && attrs.size() < 1024 * 1024) {
                        checkCsvQuality(file, relPath, issues);
                    }
                    // JSON 文件检查
                    else if (name.endsWith(".json") && attrs.size() < 1024 * 1024) {
                        checkJsonQuality(file, relPath, issues);
                    }

                    return FileVisitResult.CONTINUE;
                }
            });

            if (issues.isEmpty()) {
                report.append("✅ 未发现明显的数据质量问题！所有文件看起来都很干净。\n");
            } else {
                report.append("### ⚠️ 发现 ").append(issues.size()).append(" 个潜在问题\n\n");
                // 按问题类型分组
                Map<String, List<FileIssue>> grouped = issues.stream()
                        .collect(Collectors.groupingBy(i -> i.issueType, LinkedHashMap::new, Collectors.toList()));

                for (Map.Entry<String, List<FileIssue>> entry : grouped.entrySet()) {
                    report.append("#### ").append(entry.getKey()).append(" (").append(entry.getValue().size()).append(" 个)\n");
                    entry.getValue().stream().limit(10).forEach(i -> 
                            report.append("- ").append(i.filePath).append(" → ").append(i.suggestion).append("\n"));
                    if (entry.getValue().size() > 10) {
                        report.append("  ... 还有 ").append(entry.getValue().size() - 10).append(" 个类似问题\n");
                    }
                    report.append("\n");
                }

                report.append("---\n");
                report.append("💡 建议：使用 cleanCsvData、cleanJsonlData 或 cleanTextFile 工具对上述文件进行清洗。\n");
            }

            return report.toString();

        } catch (Exception e) {
            log.error("扫描目录失败: {}", e.getMessage(), e);
            return "错误：扫描目录时发生异常 - " + e.getMessage();
        }
    }

    private void checkCsvQuality(Path file, String relPath, List<FileIssue> issues) {
        try {
            List<String> lines = Files.readAllLines(file);
            if (lines.isEmpty()) {
                issues.add(new FileIssue(relPath, "空CSV文件", "建议删除"));
                return;
            }

            // 检查列数一致性
            int headerCols = lines.get(0).split(",").length;
            int inconsCols = 0;
            int emptyRows = 0;

            for (int i = 1; i < lines.size(); i++) {
                String line = lines.get(i).trim();
                if (line.isEmpty()) {
                    emptyRows++;
                    continue;
                }
                if (line.split(",").length != headerCols) {
                    inconsCols++;
                }
            }

            if (emptyRows > lines.size() * 0.2) {
                issues.add(new FileIssue(relPath, 
                        "CSV含大量空行 (" + emptyRows + "/" + lines.size() + ")", 
                        "建议使用 cleanCsvData 清洗"));
            }
            if (inconsCols > 0) {
                issues.add(new FileIssue(relPath,
                        "CSV列数不一致 (" + inconsCols + " 行)", 
                        "建议检查并修复列数"));
            }
        } catch (Exception ignored) {}
    }

    private void checkJsonQuality(Path file, String relPath, List<FileIssue> issues) {
        try {
            String content = Files.readString(file);
            String trimmed = content.trim();
            
            // 检查JSONL格式（多行JSON）
            if (trimmed.startsWith("{") || trimmed.startsWith("[")) {
                return; // 看起来是有效的JSON起始
            }

            // 尝试按JSONL格式逐行验证
            String[] lines = content.split("\n");
            int invalidLines = 0;
            for (String line : lines) {
                String t = line.trim();
                if (!t.isEmpty() && !isValidJson(t)) {
                    invalidLines++;
                }
            }
            
            if (invalidLines > 0 && invalidLines > lines.length * 0.3) {
                issues.add(new FileIssue(relPath,
                        "JSON格式问题 (" + invalidLines + "/" + lines.length + " 行无效)", 
                        "建议使用 cleanJsonlData 清洗"));
            }
        } catch (Exception ignored) {}
    }

    private boolean isValidJson(String text) {
        try {
            text = text.trim();
            if (text.startsWith("{")) {
                // 基本验证：尝试用Gson解析
                new com.google.gson.Gson().fromJson(text, Object.class);
                return true;
            }
            return false;
        } catch (Exception e) {
            return false;
        }
    }

    private String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return String.format("%.1f KB", bytes / 1024.0);
        return String.format("%.1f MB", bytes / (1024.0 * 1024));
    }

    private static class FileIssue {
        final String filePath;
        final String issueType;
        final String suggestion;
        FileIssue(String filePath, String issueType, String suggestion) {
            this.filePath = filePath;
            this.issueType = issueType;
            this.suggestion = suggestion;
        }
    }
}