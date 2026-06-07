import os
import json

def merge_and_clean_d2():
    raw_dir = './student-camp-data/raw/d2'
    output_path = "./phase1-basics/merged_d2.jsonl"
    unique_lines = set()

    for file_name in os.listdir(raw_dir):
        file_path = os.path.join(raw_dir, file_name)
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                clean_line = line.strip()
                if clean_line:
                    unique_lines.add(clean_line)

    with open(output_path, 'w', encoding='utf-8') as out_f:
        for line in unique_lines:
            json_data = {"text": line}
            json_string = json.dumps(json_data, ensure_ascii=False)
            out_f.write(json_string + '\n')
    print(f"🎉 成功！清洗完成，共 {len(unique_lines)} 条去重数据，已保存至 {output_path}")
if __name__ == "__main__":
    merge_and_clean_d2()