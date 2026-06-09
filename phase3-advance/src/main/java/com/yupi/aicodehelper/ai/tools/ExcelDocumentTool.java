package com.yupi.aicodehelper.ai.tools;

import dev.langchain4j.agent.tool.P;
import dev.langchain4j.agent.tool.Tool;
import lombok.extern.slf4j.Slf4j;
import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;
import org.springframework.stereotype.Component;

import java.io.FileOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

/**
 * Excel 表格生成工具
 * 用于生成 .xlsx 格式的数据表格、统计报表、学习计划表等
 */
@Slf4j
@Component
public class ExcelDocumentTool {

    private static final String OUTPUT_DIR = "generated-docs/excel";

    public ExcelDocumentTool() {
        try {
            Files.createDirectories(Paths.get(OUTPUT_DIR));
        } catch (Exception e) {
            log.error("创建输出目录失败", e);
        }
    }

    @Tool(name = "generateExcelSpreadsheet", value = """
            Generates an Excel spreadsheet (.xlsx) with the given sheet name and data.
            Use this tool when the user wants to create data tables, schedules, reports, or any spreadsheet.
            Provide column headers and row data as arrays.
            Returns the file path of the generated spreadsheet.
            """)
    public String generateExcelSpreadsheet(
            @P(value = "the name of the spreadsheet/file") String fileName,
            @P(value = "the sheet/tab name") String sheetName,
            @P(value = "the column headers") String[] columnHeaders,
            @P(value = "the row data, each row is an array of cell values") String[][] rowData) {
        try {
            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            String safeFileName = fileName.replaceAll("[\\\\/:*?\"<>|]", "_") + "_" + timestamp + ".xlsx";
            Path filePath = Paths.get(OUTPUT_DIR, safeFileName);

            try (XSSFWorkbook workbook = new XSSFWorkbook()) {
                Sheet sheet = workbook.createSheet(sheetName != null ? sheetName : "Sheet1");

                // 创建标题样式
                CellStyle headerStyle = workbook.createCellStyle();
                headerStyle.setFillForegroundColor(IndexedColors.ROYAL_BLUE.getIndex());
                headerStyle.setFillPattern(FillPatternType.SOLID_FOREGROUND);
                headerStyle.setFont(createFont(workbook, true, (short) 14, IndexedColors.WHITE.getIndex()));
                headerStyle.setAlignment(HorizontalAlignment.CENTER);
                headerStyle.setVerticalAlignment(VerticalAlignment.CENTER);
                headerStyle.setBorderBottom(BorderStyle.THIN);
                headerStyle.setBorderTop(BorderStyle.THIN);
                headerStyle.setBorderLeft(BorderStyle.THIN);
                headerStyle.setBorderRight(BorderStyle.THIN);

                // 创建数据行样式
                CellStyle dataStyle = workbook.createCellStyle();
                dataStyle.setFont(createFont(workbook, false, (short) 11, IndexedColors.BLACK.getIndex()));
                dataStyle.setAlignment(HorizontalAlignment.LEFT);
                dataStyle.setVerticalAlignment(VerticalAlignment.CENTER);
                dataStyle.setBorderBottom(BorderStyle.THIN);
                dataStyle.setBorderTop(BorderStyle.THIN);
                dataStyle.setBorderLeft(BorderStyle.THIN);
                dataStyle.setBorderRight(BorderStyle.THIN);

                // 创建交替行样式
                CellStyle altDataStyle = workbook.createCellStyle();
                altDataStyle.cloneStyleFrom(dataStyle);
                altDataStyle.setFillForegroundColor(IndexedColors.PALE_BLUE.getIndex());
                altDataStyle.setFillPattern(FillPatternType.SOLID_FOREGROUND);

                // 写入表头
                if (columnHeaders != null) {
                    Row headerRow = sheet.createRow(0);
                    for (int i = 0; i < columnHeaders.length; i++) {
                        Cell cell = headerRow.createCell(i);
                        cell.setCellValue(columnHeaders[i]);
                        cell.setCellStyle(headerStyle);
                    }
                }

                // 写入数据行
                if (rowData != null) {
                    for (int rowIdx = 0; rowIdx < rowData.length; rowIdx++) {
                        Row dataRow = sheet.createRow(rowIdx + 1);
                        String[] rowValues = rowData[rowIdx];
                        for (int colIdx = 0; colIdx < rowValues.length; colIdx++) {
                            Cell cell = dataRow.createCell(colIdx);
                            cell.setCellValue(rowValues[colIdx]);
                            // 交替行颜色
                            cell.setCellStyle(rowIdx % 2 == 0 ? dataStyle : altDataStyle);
                        }
                    }
                }

                // 自动调整列宽
                if (columnHeaders != null) {
                    for (int i = 0; i < columnHeaders.length; i++) {
                        sheet.autoSizeColumn(i);
                        // 设置最小宽度
                        if (sheet.getColumnWidth(i) < 3000) {
                            sheet.setColumnWidth(i, 3000);
                        }
                        // 设置最大宽度
                        if (sheet.getColumnWidth(i) > 20000) {
                            sheet.setColumnWidth(i, 20000);
                        }
                    }
                }

                // 写入文件
                try (FileOutputStream out = new FileOutputStream(filePath.toFile())) {
                    workbook.write(out);
                }
            }

            String absolutePath = filePath.toAbsolutePath().toString();
            log.info("Excel 表格已生成: {}", absolutePath);
            return "Excel 表格已成功生成！\n文件路径: " + absolutePath + "\n文件名: " + safeFileName;

        } catch (Exception e) {
            log.error("生成 Excel 表格失败", e);
            return "生成表格失败: " + e.getMessage();
        }
    }

    @Tool(name = "generateStudyPlan", value = """
            Generates a study plan in Excel format (.xlsx) with date, subject, tasks, and notes columns.
            Use this tool when the user wants to create a learning schedule or study plan.
            Provide the plan title and daily tasks.
            Returns the file path of the generated study plan.
            """)
    public String generateStudyPlan(
            @P(value = "the title of the study plan") String title,
            @P(value = "the daily study tasks, each item format: 'date|subject|tasks|notes'") String[] dailyTasks) {
        try {
            String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
            String safeFileName = "学习计划_" + title.replaceAll("[\\\\/:*?\"<>|]", "_") + "_" + timestamp + ".xlsx";
            Path filePath = Paths.get(OUTPUT_DIR, safeFileName);

            try (XSSFWorkbook workbook = new XSSFWorkbook()) {
                Sheet sheet = workbook.createSheet("学习计划");

                // 标题行
                Row titleRow = sheet.createRow(0);
                Cell titleCell = titleRow.createCell(0);
                titleCell.setCellValue(title);
                CellStyle titleStyle = workbook.createCellStyle();
                titleStyle.setFont(createFont(workbook, true, (short) 18, IndexedColors.DARK_BLUE.getIndex()));
                titleCell.setCellStyle(titleStyle);
                sheet.addMergedRegion(new org.apache.poi.ss.util.CellRangeAddress(0, 0, 0, 3));

                // 表头
                String[] headers = {"日期", "学习内容", "具体任务", "备注"};
                CellStyle headerStyle = workbook.createCellStyle();
                headerStyle.setFillForegroundColor(IndexedColors.LIGHT_GREEN.getIndex());
                headerStyle.setFillPattern(FillPatternType.SOLID_FOREGROUND);
                headerStyle.setFont(createFont(workbook, true, (short) 12, IndexedColors.WHITE.getIndex()));
                headerStyle.setAlignment(HorizontalAlignment.CENTER);
                headerStyle.setBorderBottom(BorderStyle.MEDIUM);

                Row headerRow = sheet.createRow(1);
                for (int i = 0; i < headers.length; i++) {
                    Cell cell = headerRow.createCell(i);
                    cell.setCellValue(headers[i]);
                    cell.setCellStyle(headerStyle);
                }

                // 数据行
                CellStyle dataStyle = workbook.createCellStyle();
                dataStyle.setFont(createFont(workbook, false, (short) 11, IndexedColors.BLACK.getIndex()));
                dataStyle.setBorderBottom(BorderStyle.THIN);
                dataStyle.setWrapText(true);

                if (dailyTasks != null) {
                    for (int i = 0; i < dailyTasks.length; i++) {
                        String[] parts = dailyTasks[i].split("\\|", 4);
                        Row row = sheet.createRow(i + 2);
                        for (int j = 0; j < Math.min(parts.length, 4); j++) {
                            Cell cell = row.createCell(j);
                            cell.setCellValue(parts[j].trim());
                            cell.setCellStyle(dataStyle);
                        }
                    }
                }

                // 设置列宽
                sheet.setColumnWidth(0, 4000);
                sheet.setColumnWidth(1, 6000);
                sheet.setColumnWidth(2, 10000);
                sheet.setColumnWidth(3, 5000);

                try (FileOutputStream out = new FileOutputStream(filePath.toFile())) {
                    workbook.write(out);
                }
            }

            String absolutePath = filePath.toAbsolutePath().toString();
            log.info("学习计划已生成: {}", absolutePath);
            return "学习计划已成功生成！\n文件路径: " + absolutePath + "\n文件名: " + safeFileName;

        } catch (Exception e) {
            log.error("生成学习计划失败", e);
            return "生成学习计划失败: " + e.getMessage();
        }
    }

    private Font createFont(Workbook workbook, boolean bold, short size, short colorIndex) {
        Font font = workbook.createFont();
        font.setBold(bold);
        font.setFontHeightInPoints(size);
        font.setColor(colorIndex);
        font.setFontName("微软雅黑");
        return font;
    }
}
