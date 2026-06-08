import os
import json

def merge_and_clean_d2():
    raw_dir = './student-camp-data/raw/d2'
    output_path = "./phase1-basics/merged_d2.jsonl"
    unique_lines = set()

    os.makedirs("./phase1-basics", exist_ok=True)
    
    with open("./phase1-basics/merge_log.txt", 'w', encoding='utf-8') as log_f:
        log_f.write("📝 开始合并文件...\n")

        if not os.path.exists(raw_dir):
            log_f.write(f"❌ 目录不存在: {raw_dir}\n")
            return

        files = os.listdir(raw_dir)
        if not files:
            log_f.write(f"⚠️ 目录为空: {raw_dir}\n")
            return

        for file_name in files:
            file_path = os.path.join(raw_dir, file_name)
            if not os.path.isfile(file_path):
                continue
            
            log_f.write(f"📂 处理文件: {file_name}\n")

            try:
                # 尝试 UTF-8 读取，如果失败尝试 GBK
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                except UnicodeDecodeError:
                    log_f.write(f"🔄 UTF-8 解码失败，尝试 GBK 编码...\n")
                    with open(file_path, 'r', encoding='gbk') as f:
                        content = f.read()

                # 去除首尾空白
                content = content.strip()
                if not content:
                    continue

                # --- 核心修改：处理不同的 JSON 格式 ---
                data_list = []
                
                # 情况 A: 文件内容以 '[' 开头，说明是一个 JSON 列表
                if content.startswith('['):
                    try:
                        data_list = json.loads(content)
                    except json.JSONDecodeError as e:
                        log_f.write(f"❌ 解析 JSON 列表失败: {e}\n")
                        continue
                
                # 情况 B: 文件内容以 '{' 开头，说明是一个 JSON 对象
                elif content.startswith('{'):
                    try:
                        data = json.loads(content)
                        # 如果对象里有 "results" 字段（如你的第二个数据块），取其值
                        if "results" in data and isinstance(data["results"], list):
                            data_list = data["results"]
                        else:
                            # 否则就把这个对象本身当作一条数据
                            data_list = [data]
                    except json.JSONDecodeError as e:
                        log_f.write(f"❌ 解析 JSON 对象失败: {e}\n")
                        continue
                
                # 情况 C: 可能是 JSONL 格式（多行），按行分割
                else:
                    lines = content.splitlines()
                    for line in lines:
                        line = line.strip()
                        if line:
                            try:
                                data_list.append(json.loads(line))
                            except:
                                log_f.write(f"⚠️ 跳过无效行: {line}\n")

                # --- 数据清洗与去重 ---
                for item in data_list:
                    # 检查有效性
                    is_valid = False
                    if 'content' in item and item['content'] and str(item['content']).strip():
                        is_valid = True
                    elif 'output' in item and item['output'] and str(item['output']).strip():
                        is_valid = True
                    elif 'text' in item and item['text'] and str(item['text']).strip():
                        is_valid = True
                    
                    if is_valid:
                        # 将对象转回 JSON 字符串存入 set 去重
                        json_str = json.dumps(item, ensure_ascii=False)
                        unique_lines.add(json_str)
                    else:
                        log_f.write(f"⚠️ 数据无效被跳过: {item}\n")

            except Exception as e:
                log_f.write(f"❌ 处理文件 {file_name} 发生未知错误: {e}\n")
                continue

        # 写入结果
        with open(output_path, 'w', encoding='utf-8') as out_f:
            for line in unique_lines:
                out_f.write(line + '\n')

        log_msg = f"🎉 成功！清洗完成，共 {len(unique_lines)} 条去重数据，已保存至 {output_path}"
        log_f.write(log_msg + "\n")
        print(log_msg)

if __name__ == "__main__":
    merge_and_clean_d2()

