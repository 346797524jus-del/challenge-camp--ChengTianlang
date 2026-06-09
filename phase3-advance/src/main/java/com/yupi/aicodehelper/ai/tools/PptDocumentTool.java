package com.yupi.aicodehelper.ai.tools;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.sl.usermodel.TextParagraph;
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

    @Tool(name = "generatePresentation", value = """
            Generates a PowerPoint presentation (.pptx) with the given title and slides.
            Use this tool when the user wants to create presentations, slide decks, or teaching materials.
            Each slide should have a title and content lines.
            Returns the file path of the generated presentation.
            """)
    public String generatePresentation(
            @P(value = "the title of the presentation") String title,
            @P(value = "the slides, each slide format: 'slideTitle|contentLine1|contentLine2|...'") String[] slides) {
        try {
            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            String safeFileName = title.replaceAll("[\\\\/:*?\"<>|]", "_") + "_" + timestamp + ".pptx";
            Path filePath = Paths.get(OUTPUT_DIR, safeFileName);

            try (XMLSlideShow ppt = new XMLSlideShow()) {
                // 设置页面大小
                ppt.setPageSize(new java.awt.Dimension(1024, 768));

                // 1. 创建封面页
                XSLFSlide titleSlide = ppt.createSlide();
                XSLFTextShape titleShape = titleSlide.createAutoShape();
                titleShape.setShapeType(org.apache.poi.sl.usermodel.ShapeType.RECT);
                titleShape.setAnchor(new java.awt.Rectangle(100, 200, 824, 200));

                XSLFTextParagraph titlePara = titleShape.addNewTextParagraph();
                titlePara.setTextAlign(TextParagraph.TextAlign.CENTER);
                XSLFTextRun titleRun = titlePara.addNewTextRun();
                titleRun.setText(title);
                titleRun.setFontSize(40.0);
                titleRun.setBold(true);
                titleRun.setFontColor(java.awt.Color.decode("#1a5276"));

                // 添加副标题
                XSLFTextParagraph subPara = titleShape.addNewTextParagraph();
                subPara.setTextAlign(TextParagraph.TextAlign.CENTER);
                XSLFTextRun subRun = subPara.addNewTextRun();
                subRun.setText("由 AI 编程小助手生成");
                subRun.setFontSize(18.0);
                subRun.setFontColor(java.awt.Color.GRAY);

                // 添加日期
                XSLFTextParagraph datePara = titleShape.addNewTextParagraph();
                datePara.setTextAlign(TextParagraph.TextAlign.CENTER);
                XSLFTextRun dateRun = datePara.addNewTextRun();
                dateRun.setText(LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyy-MM-dd")));
                dateRun.setFontSize(14.0);
                dateRun.setFontColor(java.awt.Color.LIGHT_GRAY);

                // 2. 创建内容页
                if (slides != null) {
                    for (String slideData : slides) {
                        if (slideData == null || slideData.trim().isEmpty()) continue;

                        String[] parts = slideData.split("\\|", 2);
                        String slideTitle = parts[0].trim();
                        String content = parts.length > 1 ? parts[1].trim() : "";

                        XSLFSlide contentSlide = ppt.createSlide();

                        // 幻灯片标题
                        XSLFTextShape slideTitleShape = contentSlide.createAutoShape();
                        slideTitleShape.setShapeType(org.apache.poi.sl.usermodel.ShapeType.RECT);
                        slideTitleShape.setAnchor(new java.awt.Rectangle(50, 30, 924, 60));

                        XSLFTextParagraph stPara = slideTitleShape.addNewTextParagraph();
                        XSLFTextRun stRun = stPara.addNewTextRun();
                        stRun.setText(slideTitle);
                        stRun.setFontSize(28.0);
                        stRun.setBold(true);
                        stRun.setFontColor(java.awt.Color.decode("#2c3e50"));

                        // 分隔线
                        XSLFTextShape lineShape = contentSlide.createAutoShape();
                        lineShape.setShapeType(org.apache.poi.sl.usermodel.ShapeType.RECT);
                        lineShape.setAnchor(new java.awt.Rectangle(50, 95, 924, 3));
                        lineShape.setFillColor(java.awt.Color.decode("#3498db"));

                        // 内容
                        XSLFTextShape contentShape = contentSlide.createAutoShape();
                        contentShape.setShapeType(org.apache.poi.sl.usermodel.ShapeType.RECT);
                        contentShape.setAnchor(new java.awt.Rectangle(70, 120, 884, 600));

                        String[] contentLines = content.split("\\n");
                        for (String line : contentLines) {
                            line = line.trim();
                            if (line.isEmpty()) continue;

                            XSLFTextParagraph cPara = contentShape.addNewTextParagraph();
                            cPara.setTextAlign(TextParagraph.TextAlign.LEFT);
                            cPara.setIndentLevel(0);
                            cPara.setSpaceAfter(200.0);

                            XSLFTextRun cRun = cPara.addNewTextRun();

                            // 支持简单的标记：**粗体**
                            if (line.startsWith("**") && line.endsWith("**")) {
                                cRun.setText(line.replace("**", ""));
                                cRun.setBold(true);
                                cRun.setFontSize(20.0);
                                cRun.setFontColor(java.awt.Color.decode("#2c3e50"));
                            } else if (line.startsWith("- ") || line.startsWith("• ")) {
                                cRun.setText(line);
                                cRun.setFontSize(16.0);
                                cRun.setFontColor(java.awt.Color.decode("#34495e"));
                            } else {
                                cRun.setText(line);
                                cRun.setFontSize(16.0);
                                cRun.setFontColor(java.awt.Color.decode("#34495e"));
                            }
                        }
                    }
                }

                // 3. 创建结束页
                XSLFSlide endSlide = ppt.createSlide();
                XSLFTextShape endShape = endSlide.createAutoShape();
                endShape.setShapeType(org.apache.poi.sl.usermodel.ShapeType.RECT);
                endShape.setAnchor(new java.awt.Rectangle(100, 250, 824, 200));

                XSLFTextParagraph endPara = endShape.addNewTextParagraph();
                endPara.setTextAlign(TextParagraph.TextAlign.CENTER);
                XSLFTextRun endRun = endPara.addNewTextRun();
                endRun.setText("感谢观看！");
                endRun.setFontSize(36.0);
                endRun.setBold(true);
                endRun.setFontColor(java.awt.Color.decode("#1a5276"));

                XSLFTextParagraph endSubPara = endShape.addNewTextParagraph();
                endSubPara.setTextAlign(TextParagraph.TextAlign.CENTER);
                XSLFTextRun endSubRun = endSubPara.addNewTextRun();
                endSubRun.setText("如有问题，欢迎随时提问");
                endSubRun.setFontSize(18.0);
                endSubRun.setFontColor(java.awt.Color.GRAY);

                // 写入文件
                try (FileOutputStream out = new FileOutputStream(filePath.toFile())) {
                    ppt.write(out);
                }
            }

            String absolutePath = filePath.toAbsolutePath().toString();
            log.info("PPT 演示文稿已生成: {}", absolutePath);
            return "PPT 演示文稿已成功生成！\n文件路径: " + absolutePath + "\n文件名: " + safeFileName;

        } catch (Exception e) {
            log.error("生成 PPT 失败", e);
            return "生成 PPT 失败: " + e.getMessage();
        }
    }
}
