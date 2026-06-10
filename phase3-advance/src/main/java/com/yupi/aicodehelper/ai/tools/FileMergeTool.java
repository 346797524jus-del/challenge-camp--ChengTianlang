package com.yupi.aicodehelper.ai.tools;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 文件合并工具 - 将多个数据文件合并为统一格式
 * 
 * 功能：
 * 1. CSV 文件合并
 * 2. JSON/JSONL 文件合并
 * 3. 文本文件合并
 * 4. 生成合并报告
 */
@Slf4j
@Component
public class FileMergeTool {

    private static final String MERGED_DIR = "generated-docs/merged";
    private static final DateTimeFormatter DTF = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss");

    public FileMergeTool() {
        try {
            Files.createDirectories(Paths.get(MERGED_DIR));
        } catch (Exception e) {
            log.error("创建合并输出目录失败", e);
        }
    }

    @Tool(name = "mergeCsvFiles", value = """
            Merges multiple CSV files into a single CSV file.
            Automatically detects headers from the first file and aligns columns.
            Use this when the user wants to combine multiple CSV data files.
            Returns a merge report and the path to the merged file.
            """)
    public String mergeCsvFiles(
            @P(value = "comma-separated list of CSV file paths to merge") String filePaths,
            @P(value = "whether to include header from each file (default false, uses first file header)") Boolean includeAllHeaders) {
        try {
            String[] paths = filePaths.split(",");
            List<Path> validFiles = new ArrayList<>();
            List<String> invalidPaths = new ArrayList<>();

            for (String p : paths) {
                Path path = Paths.get(p.trim());
                if (Files.exists(path) && path.toString().toLowerCase().endsWith(".csv")) {
                    validFiles.add(path);
                } else {
                    invalidPaths.add(p.trim());
                }
            }

            if (validFiles.isEmpty()) {
                return "错误：没有找到有效的 CSV 文件。提供的路径: " + filePaths;
            }

            boolean includeHeaders = includeAllHeaders != null ? includeAllHeaders : false;
            List<String> mergedLines = new ArrayList<>();
            int totalRows = 0;
            int totalDuplicates = 0;
            Set<String> seenRows = new HashSet<>();

            // 读取第一个文件的表头
            String headerLine = null;
            if (!validFiles.isEmpty()) {
                List<String> firstLines = Files.readAllLines(validFiles.get(0));
                if (!firstLines.isEmpty()) {
                    headerLine = firstLines.get(0);
                    mergedLines.add(headerLine);
                    for (int i = 1; i < firstLines.size(); i++) {
                        String line = firstLines.get(i).trim();
                        if (!line.isEmpty() && seenRows.add(line)) {
                            mergedLines.add(line);
                            totalRows++;
                        } else if (!line.isEmpty()) {
                            totalDuplicates++;
                        }
                    }
                }
            }

            // 合并其余文件
            for (int i = 1; i < validFiles.size(); i++) {
                List<String> fileLines = Files.readAllLines(validFiles.get(i));
                int startIndex = includeHeaders ? 1 : 0; // 跳过表头
                for (int j = startIndex; j < fileLines.size(); j++) {
                    String line = fileLines.get(j).trim();
                    if (!line.isEmpty() && seenRows.add(line)) {
                        mergedLines.add(line);
                        totalRows++;
                    } else if (!line.isEmpty()) {
                        totalDuplicates++;
                    }
                }
            }

            // 保存合并结果
            String mergedFileName = "merged_csv_" + DTF.format(LocalDateTime.now()) + ".csv";
            Path outputPath = Paths.get(MERGED_DIR, mergedFileName);
            Files.write(outputPath, mergedLines);

            // 生成报告
            StringBuilder report = new StringBuilder();
            report.append("## 🔗 CSV 文件合并报告\n\n");
            report.append("### 📁 合并文件列表 (").append(validFiles.size()).append(" 个)\n");
            for (Path p : validFiles) {
                try {
                    int lines = Files.readAllLines(p).size();
                    report.append("- ").append(p.getFileName()).append(" (").append(lines).append(" 行)\n");
                } catch (Exception e) {
                    report.append("- ").append(p.getFileName()).append(" (读取失败)\n");
                }
            }
            report.append("\n");
            
            if (!invalidPaths.isEmpty()) {
                report.append("### ⚠️ 无效文件 (").append(invalidPaths.size()).append(" 个)\n");
                invalidPaths.forEach(p -> report.append("- ").append(p).append("\n"));
                report.append("\n");
            }

            report.append("### 📊 合并统计\n");
            report.append("- 合并数据行数: ").append(totalRows).append("\n");
            report.append("- 去除重复行: ").append(totalDuplicates).append("\n");
            report.append("- 合并后总行数: ").append(mergedLines.size()).append("\n");
            report.append("- 输出文件: ").append(outputPath.toAbsolutePath()).append("\n");
            report.append("\n---\n");
            report.append("✅ 合并完成！文件已保存到: ").append(outputPath.toAbsolutePath());

            return report.toString();

        } catch (Exception e) {
            log.error("CSV合并失败: {}", e.getMessage(), e);
            return "错误：CSV合并时发生异常 - " + e.getMessage();
        }
    }

    @Tool(name = "mergeJsonlFiles", value = """
            Merges multiple JSONL (JSON Lines) files into a single consolidated JSONL file.
            Validates each line and removes duplicates.
            Use this when the user wants to combine multiple JSONL data files.
            Returns a merge report and the path to the merged file.
            """)
    public String mergeJsonlFiles(
            @P(value = "comma-separated list of JSONL file paths to merge") String filePaths) {
        try {
            String[] paths = filePaths.split(",");
            List<Path> validFiles = new ArrayList<>();
            List<String> invalidPaths = new ArrayList<>();

            for (String p : paths) {
                Path path = Paths.get(p.trim());
                if (Files.exists(path) && (path.toString().endsWith(".jsonl") || path.toString().endsWith(".json"))) {
                    validFiles.add(path);
                } else {
                    invalidPaths.add(p.trim());
                }
            }

            if (validFiles.isEmpty()) {
                return "错误：没有找到有效的 JSONL 文件。";
            }

            List<String> mergedLines = new ArrayList<>();
            Set<String> seenContent = new HashSet<>();
            int totalLines = 0;
            int invalidLines = 0;
            int duplicateLines = 0;

            com.google.gson.Gson gson = new com.google.gson.Gson();

            for (Path file : validFiles) {
                List<String> lines = Files.readAllLines(file, StandardCharsets.UTF_8);
                for (String line : lines) {
                    String trimmed = line.trim();
                    if (trimmed.isEmpty()) continue;

                    totalLines++;
                    
                    // 验证JSON
                    try {
                        gson.fromJson(trimmed, Object.class);
                    } catch (Exception e) {
                        invalidLines++;
                        continue;
                    }

                    // 去重
                    String key = trimmed.length() > 100 ? 
                            trimmed.substring(0, 100) + trimmed.hashCode() : trimmed;
                    if (!seenContent.add(key)) {
                        duplicateLines++;
                        continue;
                    }

                    mergedLines.add(trimmed);
                }
            }

            // 保存
            String mergedFileName = "merged_jsonl_" + DTF.format(LocalDateTime.now()) + ".jsonl";
            Path outputPath = Paths.get(MERGED_DIR, mergedFileName);
            Files.write(outputPath, mergedLines);

            StringBuilder report = new StringBuilder();
            report.append("## 🔗 JSONL 文件合并报告\n\n");
            report.append("### 📁 合并文件 (").append(validFiles.size()).append(" 个)\n");
            for (Path p : validFiles) {
                report.append("- ").append(p.getFileName()).append("\n");
            }
            report.append("\n");
            report.append("### 📊 合并统计\n");
            report.append("- 读取总行数: ").append(totalLines).append("\n");
            report.append("- 无效JSON行: ").append(invalidLines).append("\n");
            report.append("- 去重行数: ").append(duplicateLines).append("\n");
            report.append("- 合并后行数: ").append(mergedLines.size()).append("\n");
            report.append("- 输出文件: ").append(outputPath.toAbsolutePath()).append("\n");
            report.append("\n---\n");
            report.append("✅ 合并完成！");

            return report.toString();

        } catch (Exception e) {
            log.error("JSONL合并失败: {}", e.getMessage(), e);
            return "错误：JSONL合并时发生异常 - " + e.getMessage();
        }
    }

    @Tool(name = "mergeTextFiles", value = """
            Merges multiple text files into a single file with separators between each.
            Useful for combining logs, notes, or any text-based files.
            Use this when the user wants to combine multiple text files.
            Returns a merge report and the path to the merged file.
            """)
    public String mergeTextFiles(
            @P(value = "comma-separated list of text file paths to merge") String filePaths,
            @P(value = "whether to add file name headers between each file") Boolean addFileHeaders) {
        try {
            String[] paths = filePaths.split(",");
            List<Path> validFiles = new ArrayList<>();

            for (String p : paths) {
                Path path = Paths.get(p.trim());
                if (Files.exists(path) && Files.isRegularFile(path)) {
                    validFiles.add(path);
                }
            }

            if (validFiles.isEmpty()) {
                return "错误：没有找到有效的文本文件。";
            }

            boolean doHeaders = addFileHeaders != null ? addFileHeaders : true;
            List<String> mergedLines = new ArrayList<>();
            int totalLines = 0;

            String divider = "=".repeat(60);
            String subDivider = "-".repeat(40);

            for (int i = 0; i < validFiles.size(); i++) {
                Path file = validFiles.get(i);
                String fileName = file.getFileName().toString();
                List<String> fileLines = Files.readAllLines(file, StandardCharsets.UTF_8);

                if (doHeaders) {
                    if (i > 0) {
                        mergedLines.add(""); // 空行分隔
                    }
                    mergedLines.add(divider);
                    mergedLines.add("文件 " + (i + 1) + ": " + fileName);
                    mergedLines.add("路径: " + file.toAbsolutePath());
                    mergedLines.add("行数: " + fileLines.size());
                    mergedLines.add(subDivider);
                    mergedLines.add("");
                }

                // 移除BOM
                if (!fileLines.isEmpty()) {
                    String firstLine = fileLines.get(0);
                    if (!firstLine.isEmpty() && firstLine.charAt(0) == '\uFEFF') {
                        firstLine = firstLine.substring(1);
                        fileLines.set(0, firstLine);
                    }
                }

                mergedLines.addAll(fileLines);
                totalLines += fileLines.size();
            }

            // 保存
            String mergedFileName = "merged_text_" + DTF.format(LocalDateTime.now()) + ".txt";
            Path outputPath = Paths.get(MERGED_DIR, mergedFileName);
            Files.write(outputPath, mergedLines, StandardCharsets.UTF_8);

            StringBuilder report = new StringBuilder();
            report.append("## 🔗 文本文件合并报告\n\n");
            report.append("### 📁 合并文件 (").append(validFiles.size()).append(" 个)\n");
            for (Path p : validFiles) {
                try {
                    report.append("- ").append(p.getFileName())
                            .append(" (").append(Files.readAllLines(p).size()).append(" 行)\n");
                } catch (Exception e) {
                    report.append("- ").append(p.getFileName()).append(" (读取失败)\n");
                }
            }
            report.append("\n");
            report.append("### 📊 合并统计\n");
            report.append("- 源文件总数: ").append(validFiles.size()).append("\n");
            report.append("- 合并总行数: ").append(totalLines).append("\n");
            report.append("- 输出文件行数: ").append(mergedLines.size()).append("\n");
            report.append("- 输出文件: ").append(outputPath.toAbsolutePath()).append("\n");
            report.append("\n---\n");
            report.append("✅ 合并完成！");

            return report.toString();

        } catch (Exception e) {
            log.error("文本合并失败: {}", e.getMessage(), e);
            return "错误：文本合并时发生异常 - " + e.getMessage();
        }
    }

    @Tool(name = "mergeDirectoryFiles", value = """
            Merges all files of a specific type from a directory into a single consolidated file.
            Automatically finds files by extension and merges them.
            Use this when the user says 'merge all CSV files in this directory' or similar.
            Returns a merge report and the path to the merged file.
            """)
    public String mergeDirectoryFiles(
            @P(value = "the directory to scan for files") String directoryPath,
            @P(value = "file extension to filter (e.g. 'csv', 'jsonl', 'txt')") String extension,
            @P(value = "whether to scan subdirectories recursively") Boolean recursive) {
        try {
            Path rootPath = Paths.get(directoryPath).toAbsolutePath().normalize();
            if (!Files.exists(rootPath) || !Files.isDirectory(rootPath)) {
                return "错误：目录不存在 - " + directoryPath;
            }

            String ext = extension.toLowerCase().replace(".", "");
            boolean doRecursive = recursive != null ? recursive : true;

            // 收集文件
            List<Path> files = new ArrayList<>();
            int maxDepth = doRecursive ? 50 : 1;
            
            Files.walkFileTree(rootPath, EnumSet.noneOf(FileVisitOption.class), maxDepth,
                    new SimpleFileVisitor<Path>() {
                @Override
                public FileVisitResult visitFile(Path file, java.nio.file.attribute.BasicFileAttributes attrs) {
                    String name = file.getFileName().toString().toLowerCase();
                    if (name.endsWith("." + ext)) {
                        files.add(file);
                    }
                    return FileVisitResult.CONTINUE;
                }
            });

            if (files.isEmpty()) {
                return "未找到任何 ." + ext + " 文件在目录: " + rootPath;
            }

            // 调用对应的合并方法
            String filePathsJoined = files.stream()
                    .map(Path::toString)
                    .collect(Collectors.joining(","));

            return switch (ext) {
                case "csv" -> mergeCsvFiles(filePathsJoined, false);
                case "jsonl", "json" -> mergeJsonlFiles(filePathsJoined);
                default -> mergeTextFiles(filePathsJoined, true);
            };

        } catch (Exception e) {
            log.error("目录合并失败: {}", e.getMessage(), e);
            return "错误：目录合并时发生异常 - " + e.getMessage();
        }
    }
}