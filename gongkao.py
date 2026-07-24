# -*- coding: utf-8 -*-
"""考公每日一题 - AI生成+解析+Server酱推送"""
import os, json, urllib.request, urllib.parse, random
from datetime import datetime

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
SERVERCHAN_KEY = os.environ.get("SERVERCHAN_KEY", "")

def call_llm(prompt):
    url = "https://api.deepseek.com/v1/chat/completions"
    body = json.dumps({
        "model": "deepseek-v4-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7, "max_tokens": 2000
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {DEEPSEEK_API_KEY}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]

def push(title, content):
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
    data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"推送: {json.loads(resp.read().decode('utf-8')).get('code')}")

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    subjects = ["言语理解", "数量关系", "判断推理", "资料分析", "常识判断", "申论归纳概括", "申论提出对策"]
    subj = random.choice(subjects)
    
    question = call_llm(f"出一道公务员考试{subj}的真题级模拟题。行测题给ABCD四个选项，申论题给材料和要求。只出题目不给答案。")
    analysis = call_llm(f"分析这道公务员考试题目并给出详细解析：\n\n{question}\n\n格式：参考答案/解析/知识点/备考建议")
    
    content = f"## 📝 考公每日一题 ({today})\n\n**科目**: {subj}\n\n---\n\n### 题目\n\n{question}\n\n---\n\n### 📖 解析\n\n{analysis}\n\n---\n\n> 💪 每天一题，上岸可期\n> Powered by DeepSeek"
    
    os.makedirs("output", exist_ok=True)
    with open(f"output/gongkao_{today}.md", "w", encoding="utf-8") as f:
        f.write(content)
    
    push(f"📝 考公每日一题 {today}", content)
    print(f"完成: {today} {subj}")

if __name__ == "__main__":
    main()
