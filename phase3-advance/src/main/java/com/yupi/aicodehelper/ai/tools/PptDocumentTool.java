package com.yupi.aicodehelper.ai.tools;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.xslf.usermodel.*;
import org.springframework.stereotype.Component;

import java.io.FileOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * PPT 演示文稿生成工具
 * 用于生成 .pptx 格式的演示文稿
 */
@Slf4j
@Component
public class PptDocumentTool {

    private static final String OUTPUT_DIR = "generated-docs/ppt";

    public PptDocumentTool() {
        try {
            Files.createDirectories(Paths.get(OUTPUT_DIR));
        } catch (Exception e) {
            log.error("创建输出目录失败", e);
        }
    }

    /**
     * 安全地生成文件名，限制长度
     */
    private String safeFileName(String title, String extension) {
        String safe = title.replaceAll("[\\\\/:*?\"<>|]", "_");
        if (safe.length() > 80) {
            safe = safe.substring(0, 80);
        }
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        return safe + "_" + timestamp + extension;
    }

    @Tool(name = "generatePresentation", value = """
            Generates a PowerPoint presentation (.pptx) with the given title and slides.
            Use this tool when the user wants to create presentations, slide decks, or courseware.
            Each slide should have a title and content items.
            Returns the file path of the generated presentation.
            """)
    public String generatePresentation(
            @P(value = "the title of the presentation") String title,
            @P(value = "the slides, each item format: 'slideTitle|content1|content2|...'") String[] slides) {
        try {
            // 参数校验
            if (title == null || title.trim().isEmpty()) {
                return "生成演示文稿失败: 标题不能为空";
            }
            if (slides == null || slides.length == 0) {
                return "生成演示文稿失败: 幻灯片内容不能为空";
            }

            String fileName = safeFileName(title, ".pptx");
            Path filePath = Paths.get(OUTPUT_DIR, fileName);

            try (XMLSlideShow ppt = new XMLSlideShow()) {
                // 设置页面大小（宽屏 16:9）
                ppt.setPageSize(new java.awt.Dimension(1024, 576));

                // 创建标题幻灯片
                XSLFSlide titleSlide = ppt.createSlide();
                XSLFTextShape titleShape = titleSlide.createTextBox();
                titleShape.setAnchor(new java.awt.Rectangle(50, 150, 924, 200));

                XSLFTextParagraph titlePara = titleShape.addNewTextParagraph();
                titlePara.setTextAlign(XSLFTextParagraph.TextAlign.CENTER);
                XSLFTextRun titleRun = titlePara.addNewTextRun();
                titleRun.setText(title);
                titleRun.setFontSize(44.0);
                titleRun.setBold(true);
                titleRun.setFontColor(java.awt.Color.decode("#1a56db"));

                // 副标题
                XSLFTextParagraph subPara = titleShape.addNewTextParagraph();
                subPara.setTextAlign(XSLFTextParagraph.TextAlign.CENTER);
                XSLFTextRun subRun = subPara.addNewTextRun();
                subRun.setText("由 AI 编程小助手生成");
                subRun.setFontSize(18.0);
                subRun.setFontColor(java.awt.Color.GRAY);

                // 创建内容幻灯片
                for (String slide : slides) {
                    if (slide == null || slide.trim().isEmpty()) continue;

                    String[] parts = slide.split("\\|", -1);
                    String slideTitle = parts.length > 0 ? parts[0].trim() : "幻灯片";

                    XSLFSlide contentSlide = ppt.createSlide();

                    // 幻灯片标题
                    XSLFTextShape slideTitleShape = contentSlide.createTextBox();
                    slideTitleShape.setAnchor(new java.awt.Rectangle(50, 20, 924, 50));
                    XSLFTextParagraph stp = slideTitleShape.addNewTextParagraph();
                    XSLFTextRun str = stp.addNewTextRun();
                    str.setText(slideTitle);
                    str.setFontSize(28.0);
                    str.setBold(true);
                    str.setFontColor(java.awt.Color.decode("#1a56db"));

                    // 幻灯片内容
                    if (parts.length > 1) {
                        XSLFTextShape contentShape = contentSlide.createTextBox();
                        contentShape.setAnchor(new java.awt.Rectangle(50, 80, 924, 450));

                        for (int i = 1; i < parts.length; i++) {
                            String content = parts[i].trim();
                            if (content.isEmpty()) continue;

                            XSLFTextParagraph contentPara = contentShape.addNewTextParagraph();
                            contentPara.setIndentLevel(0);
                            contentPara.setSpaceAfter(10.0);

                            XSLFTextRun contentRun = contentPara.addNewTextRun();
                            contentRun.setText("• " + content);
                            contentRun.setFontSize(18.0);
                            contentRun.setFontColor(java.awt.Color.DARK_GRAY);
                        }
                    }
                }

                // 创建结束幻灯片
                XSLFSlide endSlide = ppt.createSlide();
                XSLFTextShape endShape = endSlide.createTextBox();
                endShape.setAnchor(new java.awt.Rectangle(50, 150, 924, 200));

                XSLFTextParagraph endPara = endShape.addNewTextParagraph();
                endPara.setTextAlign(XSLFTextParagraph.TextAlign.CENTER);
                XSLFTextRun endRun = endPara.addNewTextRun();
                endRun.setText("感谢观看");
                endRun.setFontSize(40.0);
                endRun.setBold(true);
                endRun.setFontColor(java.awt.Color.decode("#1a56db"));

                XSLFTextParagraph endSubPara = endShape.addNewTextParagraph();
                endSubPara.setTextAlign(XSLFTextParagraph.TextAlign.CENTER);
                XSLFTextRun endSubRun = endSubPara.addNewTextRun();
                endSubRun.setText(title);
                endSubRun.setFontSize(20.0);
                endSubRun.setFontColor(java.awt.Color.GRAY);

                // 写入文件
                try (FileOutputStream out = new FileOutputStream(filePath.toFile())) {
                    ppt.write(out);
                }
            }

            String absolutePath = filePath.toAbsolutePath().toString();
            log.info("PPT 演示文稿已生成: {}", absolutePath);
            return "PPT 演示文稿已成功生成！\n文件路径: " + absolutePath + "\n文件名: " + fileName;

        } catch (Exception e) {
            log.error("生成 PPT 演示文稿失败", e);
            return "生成演示文稿失败: " + e.getMessage();
        }
    }
}
