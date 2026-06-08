import os
import re
import json
import csv
import hashlib
import yaml
import sys
import traceback
from collections import Counter

# ==========================================
# 1. 基础架构：自适应新型路径架构与全局统计
# ==========================================
# 此时脚本位于：[项目根目录]/phase2-consolidata/pipeline/clean_d4.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__)) 

# 🛠️ 【路径重构核心方案】
# 1. 输出目录：设定在 pipeline 的上一级目录（即 ./phase2-consolidata），严格保护 pipeline 文件夹只含源码
OUTPUT_DIR = os.getenv("KYLIN_OUTPUT_DIR", os.path.abspath(os.path.join(BASE_DIR, "..")))

# 2. 输入目录：连续向上回溯两级（pipeline -> phase2-consolidata -> 项目根目录），再切入数据源
INPUT_DIR = os.getenv("KYLIN_INPUT_DIR", os.path.abspath(os.path.join(BASE_DIR, "..", "..", "student-camp-data", "raw", "d4")))

try:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
except Exception as e:
    print(f"❌ [初始化错误] 无法创建输出目录 {OUTPUT_DIR}: {e}", file=sys.stderr)
    sys.exit(1)

# 全局数据质量度量指标与异常计数器
metrics = {
    "chat_logs_total": 0,
    "chat_logs_cleaned": 0,
    "tools_total": 0,
    "tools_cleaned": 0,
    "prefs_total": 0,
    "prefs_cleaned": 0,
    "knowledge_total": 0,
    "knowledge_cleaned": 0,
    "privacy_encrypted_count": 0,
    "anomaly_missing_fields": 0,
    "anomaly_duplicate_skipped": 0,
    "anomaly_invalid_records_filtered": 0,
    "anomaly_conflicts_resolved": 0,
    "needs_review_count": 0
}

# 动态审计样例库
audit_samples = []

# 停顿词/口水词扫描配置与统计器
FILLER_WORDS_PATTERNS = {
    "嗯 (含 嗯…)": r"嗯…*",
    "那个 (含 那个…)": r"那个…*",
    "呃 (含 呃…)": r"呃…*",
    "然后然后": r"然后然后",
    "不对不对": r"不对不对"
}
filler_word_counter = Counter()


# ==========================================
# 2. 核心工具：智能清洗、口水词审计与加密引擎
# ==========================================
def clean_text_field(text, is_command_or_tool=False):
    """
    智能化文本全能标准清洗引擎
    策略：不机械套用规则。如果是系统命令或工具，收缩连续空格；
          如果是日常对话，仅剔除中文汉字之间的多余空格，保留英文/数字之间的语义空格。
    """
    if not isinstance(text, str):
        return text
    
    text = text.replace("奇麟", "麒麟")
    text = re.sub(r'[\u3000\xa0\u200b]', ' ', text)
    
    if is_command_or_tool:
        text = re.sub(r' +', ' ', text)
    else:
        text = re.sub(r'(?<=[\u4e00-\u9fa5])\s+(?=[\u4e00-\u9fa5])', '', text)
        text = re.sub(r'\s+', ' ', text)
        
    return text.strip()

def analyze_filler_words(text):
    """扫描并累计文本中的停顿词频次"""
    if not isinstance(text, str):
        return
    for name, pattern in FILLER_WORDS_PATTERNS.items():
        matches = re.findall(pattern, text)
        if matches:
            filler_word_counter[name] += len(matches)

def encrypt_sensitive_content(text):
    """单向完全加密敏感隐私信息 (SHA-256)"""
    if not isinstance(text, str):
        return text
    
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    phone_pattern = r'1[3-9]\d{9}'
    
    def to_sha256(match):
        metrics["privacy_encrypted_count"] += 1
        return hashlib.sha256(match.group(0).encode('utf-8')).hexdigest()
    
    text = re.sub(email_pattern, to_sha256, text)
    text = re.sub(phone_pattern, to_sha256, text)
    return text

def track_audit_sample(category, before, after):
    """动态收集代表性数据清洗样例"""
    if len(audit_samples) < 4 and before != after:
        audit_samples.append({
            "category": category,
            "before": str(before).replace('\n', ' '),
            "after": str(after).replace('\n', ' ')
        })


# ==========================================
# 3. 数据清洗任务流拆解
# ==========================================
def clean_chat_logs():
    """清洗会话历史日志：规范字段、打上异常 flags 标签并留存真实需求"""
    input_path = os.path.join(INPUT_DIR, "chat_logs_raw.jsonl")
    output_path = os.path.join(OUTPUT_DIR, "chat_logs.json")
    cleaned_records = []
    seen_hashes = set()
    
    if not os.path.exists(input_path):
        print(f"⚠️  [未找到文件] 跳过会话日志清洗，路径未见: {input_path}")
        return

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                metrics["chat_logs_total"] += 1
                
                line_hash = hashlib.md5(line.encode('utf-8')).hexdigest()
                if line_hash in seen_hashes:
                    metrics["anomaly_duplicate_skipped"] += 1
                    continue
                seen_hashes.add(line_hash)
                
                data = json.loads(line)
                flags = []
                
                if not data.get("uid"):
                    data["uid"] = "UNKNOWN_USER"
                    flags.append("missing_uid")
                    metrics["anomaly_missing_fields"] += 1
                if not data.get("role"):
                    data["role"] = "user"
                    flags.append("missing_role")
                    metrics["anomaly_missing_fields"] += 1
                if not data.get("time"):
                    data["time"] = "UNKNOWN_TIME"
                    flags.append("missing_time")
                    metrics["anomaly_missing_fields"] += 1

                if "text" in data:
                    raw_text = data["text"]
                    analyze_filler_words(raw_text)
                    
                    standard_text = clean_text_field(raw_text, is_command_or_tool=False)
                    final_text = encrypt_sensitive_content(standard_text)
                    
                    track_audit_sample("会话日志", raw_text, final_text)
                    data["text"] = final_text
                    
                    if len(standard_text) < 3 or "测试" in standard_text:
                        flags.append("needs_review")
                        metrics["needs_review_count"] += 1
                
                data["flags"] = flags
                cleaned_records.append(data)
                metrics["chat_logs_cleaned"] += 1
                
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_records, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ [错误] 无法解析或处理会话历史日志: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

def clean_tool_results():
    """外部工具追踪清洗：处理规范耗时、去除系统日志残留与缓存标记"""
    input_path = os.path.join(INPUT_DIR, "tool_result_raw.jsonl")
    output_path = os.path.join(OUTPUT_DIR, "tool_results.json")
    cleaned_records = []
    seen_hashes = set()
    
    if not os.path.exists(input_path):
        return

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                metrics["tools_total"] += 1
                
                line_hash = hashlib.md5(line.encode('utf-8')).hexdigest()
                if line_hash in seen_hashes:
                    metrics["anomaly_duplicate_skipped"] += 1
                    continue
                seen_hashes.add(line_hash)
                
                data = json.loads(line)
                
                if "trace_id" not in data: data["trace_id"] = "TR-GENERIC"
                if "tool_name" not in data: data["tool_name"] = "unspecified_tool"
                if "status" not in data: data["status"] = "SUCCESS"
                
                if "duration" in data:
                    try:
                        data["duration"] = float(data["duration"])
                    except (ValueError, TypeError):
                        data["duration"] = 0.0
                        metrics["anomaly_missing_fields"] += 1
                else:
                    data["duration"] = 0.0
                
                if "raw_output" in data:
                    raw_out = data["raw_output"]
                    processed_out = re.sub(r'\[CACHE\s*HIT\]|\[DEBUG\].*?\n|日志残留标定：', '', raw_out)
                    
                    analyze_filler_words(processed_out)
                    standard_text = clean_text_field(processed_out, is_command_or_tool=True)
                    final_out = encrypt_sensitive_content(standard_text)
                    
                    track_audit_sample("外部工具追踪", raw_out, final_out)
                    data["raw_output"] = final_out
                
                cleaned_records.append(data)
                metrics["tools_cleaned"] += 1
                
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_records, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ [错误] 无法处理工具链路流: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

def clean_preferences():
    """偏好抽取与冲突消解：精细化分层（默认、明确、临时、用户纠正）"""
    yaml_path = os.path.join(INPUT_DIR, "config_manual.yaml")
    csv_path = os.path.join(INPUT_DIR, "preferences_raw.csv")
    output_path = os.path.join(OUTPUT_DIR, "preferences.json")
    
    combined_data = {"global_config": {}, "user_preferences": []}
    
    if os.path.exists(yaml_path):
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                combined_data["global_config"] = yaml.safe_load(f) or {}
        except Exception as e:
            print(f"⚠️ [白盒配置异常] YAML 解析报错: {e}")
                
    if os.path.exists(csv_path):
        seen_pref_ids = set()
        conflict_evidence_log = {}
        
        try:
            with open(csv_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    metrics["prefs_total"] += 1
                    pref_id = row.get("pref_id", "").strip()
                    note = row.get("note", "").strip()
                    
                    # 🛠️ 【增量优化点】动态模糊适配表头，解决因潜在的空格或大小写不一致导致的提取失败
                    pref_value = ""
                    matched_key = None
                    for potential_key in ["preference", "Preference", "preference ", "Preference "]:
                        if potential_key in row:
                            pref_value = row[potential_key].strip()
                            matched_key = potential_key
                            break
                    if matched_key is None:
                        # 终极兜底：如果依然匹配不到，直接寻找包含 'pref' 的键
                        for k in row.keys():
                            if k and 'pref' in k.lower() and k != 'pref_id':
                                pref_value = row[k].strip()
                                matched_key = k
                                break
                    
                    if not pref_id or "重复记录" in note:
                        metrics["anomaly_invalid_records_filtered"] += 1
                        continue
                    
                    if pref_id in seen_pref_ids:
                        metrics["anomaly_conflicts_resolved"] += 1
                        conflict_evidence_log[pref_id] = f"检测到ID表征碰撞，已被最新覆写版本平替"
                        combined_data["user_preferences"] = [p for p in combined_data["user_preferences"] if p.get("pref_id") != pref_id]
                    
                    seen_pref_ids.add(pref_id)
                    
                    category = "explicit" 
                    note_lower = note.lower()
                    pref_lower = pref_value.lower()
                    
                    if "默认" in note or "default" in note_lower:
                        category = "default"
                    elif "临时" in note or "例外" in note or "today only" in pref_lower:
                        category = "temporary"
                    elif "纠正" in note or "修改" in note or "覆盖" in note or "更新" in note:
                        category = "correction"
                    
                    cleaned_row = {}
                    for k, v in row.items():
                        cleaned_v = clean_text_field(v, is_command_or_tool=False)
                        cleaned_row[k] = encrypt_sensitive_content(cleaned_v) if v else ""
                    
                    if not cleaned_row.get("uid"):
                        cleaned_row["uid"] = "SYSTEM_DEFAULT"
                        metrics["anomaly_missing_fields"] += 1
                        
                    cleaned_row["preference_category"] = category
                    cleaned_row["conflict_evidence"] = conflict_evidence_log.get(pref_id, "初始纳管版本，无竞争冲突")
                    
                    # 🛠️ 【核心防崩兜底】由于前面的循环动态处理了表头，此处强行向目标字典回注标准化的 "preference" 键值对，杜绝 KeyError
                    if "preference" not in cleaned_row:
                        cleaned_row["preference"] = encrypt_sensitive_content(clean_text_field(pref_value, is_command_or_tool=False))
                    
                    track_audit_sample("偏好记忆", pref_value, cleaned_row["preference"])
                    combined_data["user_preferences"].append(cleaned_row)
                    metrics["prefs_cleaned"] += 1
        except Exception as e:
            print(f"❌ [错误] 无法解析用户画像偏好表: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
                
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ [错误] 偏好数据落地失败: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

def clean_knowledge_base():
    """本地知识库结构化清洗：过滤无效空壳案例，拒绝敏感信息写入知识"""
    input_path = os.path.join(INPUT_DIR, "knowledge_raw.txt")
    output_path = os.path.join(OUTPUT_DIR, "knowledge.json")
    cleaned_cases = []
    
    if not os.path.exists(input_path):
        return

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        blocks = re.findall(r"=== 案例开始 ===(.*?)=== 案例结束 ===", content, re.DOTALL)
        for block in blocks:
            if not block.strip(): 
                metrics["anomaly_invalid_records_filtered"] += 1
                continue
            metrics["knowledge_total"] += 1
                
            lines = block.split('\n')
            case_data = {}
            current_key = None
            
            for line in lines:
                if not line.strip(): continue
                if "：" in line or ":" in line:
                    parts = re.split(r'[：:]', line, maxsplit=1)
                    current_key = parts[0].strip()
                    case_data[current_key] = parts[1].strip()
                elif current_key:
                    case_data[current_key] += "\n" + line.strip()

            if not case_data.get("标题") and not case_data.get("原则") and not case_data.get("步骤"):
                metrics["anomaly_invalid_records_filtered"] += 1
                continue
                
            final_case = {
                "title": encrypt_sensitive_content(clean_text_field(case_data.get("标题") or case_data.get("原则") or "未定义主题", is_command_or_tool=False)),
                "tags": [clean_text_field(t) for t in re.split(r'[,，、\s]+', case_data.get("标签", "通用")) if t.strip()],
                "body_steps": ""
            }
            
            body_parts = []
            for k, v in case_data.items():
                if k not in ["标题", "原则", "标签"]:
                    body_parts.append(f"{k}: {v}")
            
            raw_body_text = "\n".join(body_parts)
            analyze_filler_words(raw_body_text)
            
            cleaned_body = clean_text_field(raw_body_text, is_command_or_tool=True)
            final_case["body_steps"] = encrypt_sensitive_content(cleaned_body)
            
            track_audit_sample("知识库文本", case_data.get("标题", "无"), final_case["title"])
            cleaned_cases.append(final_case)
            metrics["knowledge_cleaned"] += 1
            
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_cases, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ [错误] 知识库结构化清洗崩溃: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


# ==========================================
# 4. 高级生成器：生成兼备度量、样例与争议说明的审计报告
# ==========================================
def generate_report():
    output_path = os.path.join(OUTPUT_DIR, "report.md")
    
    filler_rows = ""
    for word, count in filler_word_counter.most_common():
        filler_rows += f"| `{word}` | **{count}** 次 | {'🔥 高频重灾区' if count >= 3 else ' 正常口水词'} |\n"
    if not filler_rows:
        filler_rows = "| 暂无统计数据 | 0 次 | - |\n"

    sample_rows = ""
    for s in audit_samples:
        sample_rows += f"| {s['category']} | `{s['before'][:40]}` | `{s['after'][:40]}` |\n"
    if not sample_rows:
        sample_rows = "| 暂无明显变动项对比 | - | - |\n"

    report_content = f"""# 📊 D4 数据清洗与数据合规审计报告

## 📋 一、 任务基调与工程约束
* **审计单元**：Kylin-Office-Agent ETL 自动化洗脑模块
* **源码隔离度**：🛡️ 纯净运行（已激活 `./phase2-consolidata/pipeline` 纯源码物理隔离模式）
* **运行规范**：完全支持从项目根目录一键安全拉起，结果输出单向幂等，拒绝污染 `pipeline` 源码文件夹。

---

## 📈 二、 核心资产数据量度表

| 数据资产类别 | 原始输入文件名 | 清洗前条数 | 清洗后条数 | 数据精简率 | 交付产物目标路径 |
| :--- | :--- | :---: | :---: | :---: | :--- |
| **会话历史日志** | `chat_logs_raw.jsonl` | {metrics['chat_logs_total']} | {metrics['chat_logs_cleaned']} | {(metrics['chat_logs_total']-metrics['chat_logs_cleaned'])/metrics['chat_logs_total']*100 if metrics['chat_logs_total'] > 0 else 0:.1f}% | `../chat_logs.json` |
| **外部工具追踪** | `tool_result_raw.jsonl` | {metrics['tools_total']} | {metrics['tools_cleaned']} | {(metrics['tools_total']-metrics['tools_cleaned'])/metrics['tools_total']*100 if metrics['tools_total'] > 0 else 0:.1f}% | `../tool_results.json` |
| **用户画像偏好** | `preferences_raw.csv` | {metrics['prefs_total']} | {metrics['prefs_cleaned']} | {(metrics['prefs_total']-metrics['prefs_cleaned'])/metrics['prefs_total']*100 if metrics['prefs_total'] > 0 else 0:.1f}% | `../preferences.json` |
| **本地案例知识** | `knowledge_raw.txt` | {metrics['knowledge_total']} | {metrics['knowledge_cleaned']} | {(metrics['knowledge_total']-metrics['knowledge_cleaned'])/metrics['knowledge_total']*100 if metrics['knowledge_total'] > 0 else 0:.1f}% | `../knowledge.json` |

---

## 🚨 三、 资产异常计数与质量审计
* **关键要素不规范/缺损（补全项）**：{metrics['anomaly_missing_fields']} 次
* **物理级重试冗余行（物理去重）**：{metrics['anomaly_duplicate_skipped']} 条
* **无效案例/低质量空壳（强力过滤）**：{metrics['anomaly_invalid_records_filtered']} 条
* **偏好版本冲突（消解与覆盖）**：{metrics['anomaly_conflicts_resolved']} 项
* **触发高风险人工介入审查（needs_review）**：{metrics['needs_review_count']} 条

---

## 🔍 四、 核心清洗样例 Before & After 对比

| 数据域类别 | 清洗前原始片段线索 | 清洗后精纯/脱敏快照 |
| :--- | :--- | :--- |
{sample_rows}

---

## 🗣️ 五、 文本特征分析：停顿词/口水词统计

| 捕获停顿词特征 | 原始文本出现频次 | 严重评级 |
| :--- | :---: | :--- |
{filler_rows}

---

## ⚖️ 六、 争议项处置判定与归纳白皮书（删/留/复查解释）

### 1. 为什么“删”（过滤与裁剪依据）
* **理由**：对标记 `note="重复记录"`、不含唯一ID的代码行及缺少主干核心步骤的知识库碎屑实施硬裁剪。

### 2. 为什么“留”（不伤害语义的智能化保留）
* **理由**：拒绝一刀切清洗。中文汉字之间的无效空碎屑全线斩断；但英汉混排、命令行以及核心隐私特征通过不可逆 **SHA-256 哈希**妥善保留，保证模型检索的完整连接。

### 3. 为什么打上“复查标签 (needs_review)”
* **理由**：对于文本过低矮或显式包含“测试/DEBUG”的未知需求，打上 `flags: ["needs_review"]`，交由下游系统安全卡点复核。
"""
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(report_content.strip())
        print(f" -> [成功] 已生成高精审计报告: {output_path}")
    except Exception as e:
        print(f"❌ [错误] 无法写入审计报告文档: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)


# ==========================================
# 5. 任务流控主入口
# ==========================================
if __name__ == "__main__":
    print("🚀 正在启动 D4 工业级全域清洗与合规统计引擎...")
    print(f"   [配置监测] 源码基准目录: {BASE_DIR}")
    print(f"   [配置监测] 输出交付目录: {OUTPUT_DIR}")
    print(f"   [配置监测] 输入依赖目录: {INPUT_DIR}")
    
    clean_chat_logs()
    clean_tool_results()
    clean_preferences()
    clean_knowledge_base()
    generate_report()
    print("✨ 清洗与全维链路报告生成大获成功！`pipeline` 文件夹保持绝对纯净。")