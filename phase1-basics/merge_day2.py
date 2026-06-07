import os
import json

def merge_and_clean_d2():
    raw_dir = './student-camp-data/raw/d2'
    output_path = "./phase1-basics/merged_d2.jsonl"
    unique_lines = set()

    os.makedirs("./phase1-basics", exist_ok=True)
    log_f = open("./phase1-basics/merge_log.txt", 'w', encoding='utf-8')
    log_f.write("📝 开始合并文件...\n")

    files = os.listdir(raw_dir)
    for file_name in files:
        file_path = os.path.join(raw_dir, file_name)
        log_f.write(f"📂 处理文件: {file_name}\n")

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                clean_line = line.strip()
                if clean_line:
                    try:
                        data = json.loads(clean_line)
                        if 'text' not in data or not data['text'].strip():
                            log_f.write(f"⚠️ 发现空文本行，已跳过: {clean_line}\n")
                            continue
                    except json.JSONDecodeError:
                        log_f.write(f"❌ 无法解析的 JSON 行，已跳过: {clean_line}\n")
                        continue
                    unique_lines.add(clean_line)
                    

    with open(output_path, 'w', encoding='utf-8') as out_f:
        for line in unique_lines:
            json_data = {"text": line}
            json_string = json.dumps(json_data, ensure_ascii=False)
            out_f.write(json_string + '\n')

    log_f.write(f"🎉 成功！清洗完成，共 {len(unique_lines)} 条去重数据，已保存至 {output_path}")
    print(f"🎉 成功！清洗完成，共 {len(unique_lines)} 条去重数据，已保存至 {output_path}")
    log_f.close()

if __name__ == "__main__":
    merge_and_clean_d2()