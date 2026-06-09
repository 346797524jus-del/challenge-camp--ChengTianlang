package com.yupi.aicodehelper.ai.tools;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.xwpf.usermodel.*;
import org.springframework.stereotype.Component;

import java.io.FileOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Word 文档生成工具
 * 用于生成 .docx 格式的简历、报告、学习计划等文档
 */
@Slf4j
@Component
public class WordDocumentTool {

    private static final String OUTPUT_DIR = "generated-docs/word";

    public WordDocumentTool() {
        // 确保输出目录存在
        try {
            Files.createDirectories(Paths.get(OUTPUT_DIR));
        } catch (Exception e) {
            log.error("创建输出目录失败", e);
        }
    }

    @Tool(name = "generateWordDocument", value = """
            Generates a Word document (.docx) with the given title and content.
            Use this tool when the user wants to create resumes, reports, study plans, or any Word document.
            The content should be provided as paragraphs, each paragraph is a separate section.
            Returns the file path of the generated document.
            """)
    public String generateWordDocument(
            @P(value = "the title of the document") String title,
            @P(value = "the content paragraphs, each paragraph is a separate section") String[] paragraphs,
            @P(value = "the author name, optional") String author) {
        try {
            // 生成文件名
            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            String fileName = title.replaceAll("[\\\\/:*?\"<>|]", "_") + "_" + timestamp + ".docx";
            Path filePath = Paths.get(OUTPUT_DIR, fileName);

            try (XWPFDocument document = new XWPFDocument()) {
                // 设置文档基本信息
                if (author != null && !author.isEmpty()) {
                    document.getProperties().getCoreProperties().setCreator(author);
                }

                // 添加标题
                XWPFParagraph titleParagraph = document.createParagraph();
                titleParagraph.setAlignment(ParagraphAlignment.CENTER);
                XWPFRun titleRun = titleParagraph.createRun();
                titleRun.setText(title);
                titleRun.setBold(true);
                titleRun.setFontSize(22);
                titleRun.setFontFamily("微软雅黑");
                titleRun.addBreak();

                // 添加分隔线
                XWPFParagraph separator = document.createParagraph();
                separator.setAlignment(ParagraphAlignment.CENTER);
                XWPFRun sepRun = separator.createRun();
                sepRun.setText("————————————————————");
                sepRun.setFontSize(10);
                sepRun.setColor("999999");

                // 添加内容段落
                for (String paragraph : paragraphs) {
                    if (paragraph == null || paragraph.trim().isEmpty()) {
                        continue;
                    }

                    XWPFParagraph contentParagraph = document.createParagraph();
                    contentParagraph.setAlignment(ParagraphAlignment.LEFT);
                    contentParagraph.setSpacingAfter(200);
                    contentParagraph.setFirstLineIndent(400); // 首行缩进

                    XWPFRun contentRun = contentParagraph.createRun();
                    contentRun.setText(paragraph);
                    contentRun.setFontSize(12);
                    contentRun.setFontFamily("宋体");
                    contentRun.addBreak();
                }

                // 添加页脚信息
                XWPFParagraph footerParagraph = document.createParagraph();
                footerParagraph.setAlignment(ParagraphAlignment.RIGHT);
                XWPFRun footerRun = footerParagraph.createRun();
                footerRun.setText("由 AI 编程小助手生成 - " + LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")));
                footerRun.setFontSize(9);
                footerRun.setColor("999999");
                footerRun.setItalic(true);

                // 写入文件
                try (FileOutputStream out = new FileOutputStream(filePath.toFile())) {
                    document.write(out);
                }
            }

            String absolutePath = filePath.toAbsolutePath().toString();
            log.info("Word 文档已生成: {}", absolutePath);
            return "文档已成功生成！\n文件路径: " + absolutePath + "\n文件名: " + fileName;

        } catch (Exception e) {
            log.error("生成 Word 文档失败", e);
            return "生成文档失败: " + e.getMessage();
        }
    }

    @Tool(name = "generateResume", value = """
            Generates a professional resume/cv in Word format (.docx).
            Use this tool when the user wants to create a resume or CV.
            Provide personal info, education, work experience, skills, and projects.
            Returns the file path of the generated resume.
            """)
    public String generateResume(
            @P(value = "the person's full name") String name,
            @P(value = "the person's contact info like phone, email") String contactInfo,
            @P(value = "the person's education background") String[] education,
            @P(value = "the person's work experience") String[] workExperience,
            @P(value = "the person's skills") String[] skills,
            @P(value = "the person's projects") String[] projects) {
        try {
            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            String fileName = "简历_" + name + "_" + timestamp + ".docx";
            Path filePath = Paths.get(OUTPUT_DIR, fileName);

            try (XWPFDocument document = new XWPFDocument()) {
                // 标题 - 姓名
                XWPFParagraph namePara = document.createParagraph();
                namePara.setAlignment(ParagraphAlignment.CENTER);
                XWPFRun nameRun = namePara.createRun();
                nameRun.setText(name);
                nameRun.setBold(true);
                nameRun.setFontSize(26);
                nameRun.setFontFamily("微软雅黑");

                // 联系方式
                if (contactInfo != null && !contactInfo.isEmpty()) {
                    XWPFParagraph contactPara = document.createParagraph();
                    contactPara.setAlignment(ParagraphAlignment.CENTER);
                    XWPFRun contactRun = contactPara.createRun();
                    contactRun.setText(contactInfo);
                    contactRun.setFontSize(11);
                    contactRun.setColor("555555");
                }

                // 教育背景
                addResumeSection(document, "📚 教育背景", education);

                // 工作经历
                addResumeSection(document, "💼 工作经历", workExperience);

                // 技能特长
                addResumeSection(document, "🛠 技能特长", skills);

                // 项目经验
                addResumeSection(document, "🚀 项目经验", projects);

                try (FileOutputStream out = new FileOutputStream(filePath.toFile())) {
                    document.write(out);
                }
            }

            String absolutePath = filePath.toAbsolutePath().toString();
            log.info("简历已生成: {}", absolutePath);
            return "简历已成功生成！\n文件路径: " + absolutePath + "\n文件名: " + fileName;

        } catch (Exception e) {
            log.error("生成简历失败", e);
            return "生成简历失败: " + e.getMessage();
        }
    }

    private void addResumeSection(XWPFDocument document, String sectionTitle, String[] items) {
        if (items == null || items.length == 0) {
            return;
        }

        // 章节标题
        XWPFParagraph titlePara = document.createParagraph();
        titlePara.setSpacingBefore(400);
        XWPFRun titleRun = titlePara.createRun();
        titleRun.setText(sectionTitle);
        titleRun.setBold(true);
        titleRun.setFontSize(14);
        titleRun.setFontFamily("微软雅黑");
        titleRun.addBreak();

        // 分隔线
        XWPFParagraph sepPara = document.createParagraph();
        XWPFRun sepRun = sepPara.createRun();
        sepRun.setText("─────────────────────");
        sepRun.setFontSize(8);
        sepRun.setColor("CCCCCC");

        // 内容项
        for (String item : items) {
            if (item == null || item.trim().isEmpty()) continue;
            XWPFParagraph itemPara = document.createParagraph();
            itemPara.setSpacingAfter(100);
            XWPFRun itemRun = itemPara.createRun();
            itemRun.setText("• " + item);
            itemRun.setFontSize(11);
            itemRun.setFontFamily("宋体");
        }
    }
}
