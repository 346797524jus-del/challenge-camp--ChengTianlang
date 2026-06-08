import os
import re
import pandas as pd

# 读取数据
df = pd.read_csv("./student-camp-data/raw/d3/chat_sessions_dirty.csv", 
                 encoding='utf-8',
                 header=None,  # 不将第一行作为表头
                 names=['session_id', 'user_id', 'role', 'message', 'created_at'])  # 手动指定列名

# 1. 去除首尾空格
for col in df.select_dtypes(include=['object', 'string']).columns:
    df[col] = df[col].str.strip()

# 2. 定义一个函数来清洗 HTML 标签
def remove_html_tags(text):
    if not isinstance(text, str):
        return text
    # 正则表达式：匹配 <...> 这种格式的标签并替换为空字符串
    # ? 表示非贪婪匹配，确保只匹配标签本身
    clean_text = re.sub(r'<.*?>', '', text)
    return clean_text

# 3. 将清洗函数应用到 'message' 列 (如果需要其他列也清洗，可以添加到列表中)
# 注意：我们只对 message 列进行深度清洗，以免破坏 session_id 等数据
if 'message' in df.columns:
    df['message'] = df['message'].apply(remove_html_tags)
    # 清洗完标签后，可能产生新的首尾空格，再次 strip 一下
    df['message'] = df['message'].str.strip()

# 4. 删除全为空的行
df = df.dropna(how='all')

# 5. 删除 message 为空的行
if 'message' in df.columns:
    df = df.dropna(subset=['message'])
    df = df[df['message'].str.strip() != '']

# 6. 去重
df = df.drop_duplicates()

# 7. 删除重复的表头行 (如果文件里混杂了表头)
header_mask = (df['session_id'] == 'session_id') & \
              (df['user_id'] == 'user_id') & \
              (df['role'] == 'role') & \
              (df['message'] == 'message') & \
              (df['created_at'] == 'created_at')
df = df[~header_mask]

# 保存结果
os.makedirs("./phase1-basics", exist_ok=True)
df.to_csv("./phase1-basics/cleaned_dirty.csv", 
          index=False, 
          encoding='utf-8',
          header=False)  

print(f"🎉 成功！清洗完成，共 {len(df)} 条数据，已保存至 ./phase1-basics/cleaned_dirty.csv")
