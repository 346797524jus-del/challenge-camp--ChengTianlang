package com.yupi.aicodehelper.ai.tools;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.File;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 项目扫描工具 - 扫描项目文件结构、统计信息、识别文件类型
 * 
 * 功能：
 * 1. 递归扫描目录结构
 * 2. 统计各类型文件数量和大小
 * 3. 识别代码文件、配置文件、文档文件
 * 4. 生成项目结构摘要报告
 */
@Slf4j
@Component
public class ProjectScannerTool {

    // 常见代码文件扩展名
    private static final Set<String> CODE_EXTENSIONS = Set.of(
            "java", "py", "js", "ts", "jsx", "tsx", "vue", "html", "css", "scss",
            "go", "rs", "cpp", "c", "h", "hpp", "cs", "rb", "php", "swift", "kt"
    );

    // 配置文件扩展名
    private static final Set<String> CONFIG_EXTENSIONS = Set.of(
            "yml", "yaml", "json", "xml", "properties", "env", "ini", "cfg", "toml",
            "gradle", "pom", "lock", "gitignore", "dockerignore"
    );

    // 文档文件扩展名
    private static final Set<String> DOC_EXTENSIONS = Set.of(
            "md", "txt", "rst", "adoc", "pdf", "docx", "xlsx", "pptx", "csv"
    );

    // 排除的目录
    private static final Set<String> EXCLUDED_DIRS = Set.of(
            "node_modules", ".git", "__pycache__", ".idea", ".vscode",
            "target", "build", "dist", ".next", "venv", ".venv", "vendor"
    );

    @Tool(name = "scanProjectStructure", value = """
            Scans a project directory and returns its file structure, statistics, and summary.
            Use this when the user wants to analyze, clean, or understand a project's structure.
            Returns a formatted report with file counts, sizes, and categorized file lists.
            """)
    public String scanProjectStructure(
            @P(value = "the directory path to scan") String directoryPath,
            @P(value = "whether to recursively scan subdirectories (default true)") Boolean recursive) {
        try {
            Path rootPath = Paths.get(directoryPath).toAbsolutePath().normalize();
            
            if (!Files.exists(rootPath)) {
                return "错误：目录不存在 - " + rootPath.toString();
            }
            if (!Files.isDirectory(rootPath)) {
                return "错误：路径不是目录 - " + rootPath.toString();
            }

            boolean doRecursive = recursive != null ? recursive : true;

            // 收集统计信息
            ProjectStats stats = new ProjectStats();
            
            if (doRecursive) {
                Files.walkFileTree(rootPath, EnumSet.noneOf(FileVisitOption.class), 50, 
                        new SimpleFileVisitor<Path>() {
                    @Override
                    public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) {
                        String dirName = dir.getFileName().toString();
                        if (EXCLUDED_DIRS.contains(dirName)) {
                            return FileVisitResult.SKIP_SUBTREE;
                        }
                        stats.dirCount++;
                        return FileVisitResult.CONTINUE;
                    }

                    @Override
                    public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                        if (attrs.isRegularFile()) {
                            stats.totalFiles++;
                            stats.totalSize += attrs.size();
                            
                            String fileName = file.getFileName().toString();
                            String ext = getExtension(fileName);
                            
                            FileInfo info = new FileInfo();
                            info.relativePath = rootPath.relativize(file).toString();
                            info.size = attrs.size();
                            info.lastModified = LocalDateTime.ofInstant(
                                    Instant.ofEpochMilli(attrs.lastModifiedTime().toMillis()),
                                    ZoneId.systemDefault());
                            info.extension = ext;

                            // 分类
                            if (CODE_EXTENSIONS.contains(ext.toLowerCase())) {
                                stats.codeFiles.add(info);
                            } else if (CONFIG_EXTENSIONS.contains(ext.toLowerCase())) {
                                stats.configFiles.add(info);
                            } else if (DOC_EXTENSIONS.contains(ext.toLowerCase())) {
                                stats.docFiles.add(info);
                            } else if (!ext.isEmpty()) {
                                stats.otherFiles.add(info);
                            } else {
                                stats.noExtensionFiles.add(info);
                            }
                        }
                        return FileVisitResult.CONTINUE;
                    }

                    @Override
                    public FileVisitResult visitFileFailed(Path file, java.io.IOException exc) {
                        stats.errorCount++;
                        return FileVisitResult.CONTINUE;
                    }
                });
            } else {
                // 仅扫描顶层
                File[] files = rootPath.toFile().listFiles();
                if (files != null) {
                    for (File f : files) {
                        if (f.isDirectory()) {
                            stats.dirCount++;
                        } else {
                            stats.totalFiles++;
                            stats.totalSize += f.length();
                            FileInfo info = new FileInfo();
                            info.relativePath = f.getName();
                            info.size = f.length();
                            info.lastModified = LocalDateTime.ofInstant(
                                    Instant.ofEpochMilli(f.lastModified()),
                                    ZoneId.systemDefault());
                            info.extension = getExtension(f.getName());
                            stats.codeFiles.add(info);
                        }
                    }
                }
            }

            // 生成报告
            return buildReport(rootPath, stats);

        } catch (Exception e) {
            log.error("扫描项目结构失败: {}", e.getMessage(), e);
            return "错误：扫描项目结构时发生异常 - " + e.getMessage();
        }
    }

    @Tool(name = "analyzeProjectDeep", value = """
            Deep analyzes a project, providing statistics on code files, sizes, and key findings.
            Use this when the user asks for detailed project analysis, code statistics, or wants to know
            the project's composition.
            Returns a detailed analysis report.
            """)
    public String analyzeProjectDeep(
            @P(value = "the directory path to analyze") String directoryPath,
            @P(value = "analysis focus: 'code', 'types', or 'all' (default 'all')") String focus) {
        try {
            // 先做基本扫描
            String scanResult = scanProjectStructure(directoryPath, true);
            
            Path rootPath = Paths.get(directoryPath).toAbsolutePath().normalize();
            
            StringBuilder analysis = new StringBuilder();
            analysis.append("## 🔬 项目深度分析报告\n\n");
            analysis.append("分析目录: ").append(rootPath).append("\n");
            analysis.append("分析时间: ").append(LocalDateTime.now()
                    .format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))).append("\n\n");

            // 收集所有文件
            List<Path> allFiles = new ArrayList<>();
            if (Files.exists(rootPath)) {
                Files.walkFileTree(rootPath, EnumSet.noneOf(FileVisitOption.class), 50,
                        new SimpleFileVisitor<Path>() {
                    @Override
                    public FileVisitResult preVisitDirectory(Path dir, BasicFileAttributes attrs) {
                        if (EXCLUDED_DIRS.contains(dir.getFileName().toString())) {
                            return FileVisitResult.SKIP_SUBTREE;
                        }
                        return FileVisitResult.CONTINUE;
                    }
                    @Override
                    public FileVisitResult visitFile(Path file, BasicFileAttributes attrs) {
                        if (attrs.isRegularFile()) {
                            allFiles.add(file);
                        }
                        return FileVisitResult.CONTINUE;
                    }
                });
            }

            // 统计扩展名分布
            Map<String, Long> extCount = allFiles.stream()
                    .map(f -> getExtension(f.getFileName().toString()).toLowerCase())
                    .filter(e -> !e.isEmpty())
                    .collect(Collectors.groupingBy(e -> e, Collectors.counting()));

            analysis.append("### 📊 文件类型分布\n");
            extCount.entrySet().stream()
                    .sorted(Map.Entry.<String, Long>comparingByValue().reversed())
                    .limit(15)
                    .forEach(e -> analysis.append(String.format("- .%-10s : %d 个文件\n", e.getKey(), e.getValue())));

            // 最大的文件
            analysis.append("\n### 📦 最大文件 (Top 10)\n");
            allFiles.stream()
                    .sorted((a, b) -> {
                        try {
                            return Long.compare(Files.size(b), Files.size(a));
                        } catch (Exception ex) { return 0; }
                    })
                    .limit(10)
                    .forEach(f -> {
                        try {
                            long size = Files.size(f);
                            String relPath = rootPath.relativize(f).toString();
                            analysis.append(String.format("- %s (%s)\n", relPath, formatSize(size)));
                        } catch (Exception ignored) {}
                    });

            // 总计
            long totalSize = allFiles.stream().mapToLong(f -> {
                try { return Files.size(f); } catch (Exception ex) { return 0; }
            }).sum();
            analysis.append("\n### 📈 总体统计\n");
            analysis.append("- 总文件数: ").append(allFiles.size()).append("\n");
            analysis.append("- 总大小: ").append(formatSize(totalSize)).append("\n");
            analysis.append("- 文件类型数: ").append(extCount.size()).append("\n");

            return analysis.toString();

        } catch (Exception e) {
            log.error("深度分析失败: {}", e.getMessage(), e);
            return "错误：深度分析时发生异常 - " + e.getMessage();
        }
    }

    private String buildReport(Path rootPath, ProjectStats stats) {
        StringBuilder report = new StringBuilder();
        
        report.append("## 📂 项目扫描报告\n\n");
        report.append("扫描目录: ").append(rootPath).append("\n");
        report.append("扫描时间: ").append(LocalDateTime.now()
                .format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"))).append("\n\n");

        // 总体统计
        report.append("### 📊 总体统计\n");
        report.append("- 总文件数: ").append(stats.totalFiles).append("\n");
        report.append("- 总大小: ").append(formatSize(stats.totalSize)).append("\n");
        report.append("- 子目录数: ").append(stats.dirCount).append("\n");
        if (stats.errorCount > 0) {
            report.append("- ⚠️ 无法读取文件数: ").append(stats.errorCount).append("\n");
        }
        report.append("\n");

        // 分类统计
        report.append("### 📁 文件分类\n");
        report.append("- 代码文件: ").append(stats.codeFiles.size()).append(" 个\n");
        report.append("- 配置文件: ").append(stats.configFiles.size()).append(" 个\n");
        report.append("- 文档文件: ").append(stats.docFiles.size()).append(" 个\n");
        report.append("- 其他文件: ").append(stats.otherFiles.size()).append(" 个\n");
        report.append("- 无扩展名文件: ").append(stats.noExtensionFiles.size()).append(" 个\n");
        report.append("\n");

        // 代码文件列表（前20个）
        if (!stats.codeFiles.isEmpty()) {
            report.append("### 💻 代码文件 (前20个)\n");
            stats.codeFiles.stream()
                    .limit(20)
                    .forEach(f -> report.append(String.format("- %s (%s)\n", 
                            f.relativePath, formatSize(f.size))));
            if (stats.codeFiles.size() > 20) {
                report.append("  ... 还有 ").append(stats.codeFiles.size() - 20).append(" 个代码文件\n");
            }
            report.append("\n");
        }

        // 配置文件列表
        if (!stats.configFiles.isEmpty()) {
            report.append("### ⚙️ 配置文件\n");
            stats.configFiles.forEach(f -> report.append("- ").append(f.relativePath).append("\n"));
            report.append("\n");
        }

        // 文档文件列表
        if (!stats.docFiles.isEmpty()) {
            report.append("### 📝 文档文件\n");
            stats.docFiles.forEach(f -> report.append("- ").append(f.relativePath).append("\n"));
            report.append("\n");
        }

        report.append("---\n");
        report.append("✅ 扫描完成！如需对项目进行清洗或合并操作，请使用其他工具。\n");

        return report.toString();
    }

    private String getExtension(String fileName) {
        int dotIndex = fileName.lastIndexOf('.');
        if (dotIndex > 0 && dotIndex < fileName.length() - 1) {
            return fileName.substring(dotIndex + 1);
        }
        return "";
    }

    private String formatSize(long bytes) {
        if (bytes < 1024) return bytes + " B";
        if (bytes < 1024 * 1024) return String.format("%.1f KB", bytes / 1024.0);
        if (bytes < 1024 * 1024 * 1024) return String.format("%.1f MB", bytes / (1024.0 * 1024));
        return String.format("%.2f GB", bytes / (1024.0 * 1024 * 1024));
    }

    // 内部数据类
    private static class ProjectStats {
        int totalFiles = 0;
        long totalSize = 0;
        int dirCount = 0;
        int errorCount = 0;
        List<FileInfo> codeFiles = new ArrayList<>();
        List<FileInfo> configFiles = new ArrayList<>();
        List<FileInfo> docFiles = new ArrayList<>();
        List<FileInfo> otherFiles = new ArrayList<>();
        List<FileInfo> noExtensionFiles = new ArrayList<>();
    }

    private static class FileInfo {
        String relativePath;
        long size;
        LocalDateTime lastModified;
        String extension;
    }
}