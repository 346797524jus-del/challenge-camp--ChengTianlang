import os
import sys
import pandas as pd


df = pd.read_csv("./student-camp-data/raw/d3/chat_sessions_dirty.csv", 
                 encoding='utf-8',
                 header=None,  # 不将第一行作为表头
                 names=['session_id', 'user_id', 'role', 'message', 'created_at'])  # 手动指定列名

for col in df.select_dtypes(include=['object', 'string']).columns:
    df[col] = df[col].str.strip()

df = df.dropna(how='all')

if 'message' in df.columns:
    df = df.dropna(subset=['message'])
    df = df[df['message'].str.strip() != '']

df = df.drop_duplicates()

header_mask = (df['session_id'] == 'session_id') & \
              (df['user_id'] == 'user_id') & \
              (df['role'] == 'role') & \
              (df['message'] == 'message') & \
              (df['created_at'] == 'created_at')
df = df[~header_mask]

os.makedirs("./phase1-basics", exist_ok=True)
df.to_csv("./phase1-basics/cleaned_dirty.csv", 
          index=False, 
          encoding='utf-8',
          header=False)  

print(f"🎉 成功！合并完成，共 {len(df)} 条数据，已保存至 ./phase1-basics/cleaned_dirty.csv")
