# -*- coding: utf-8 -*-
"""
每日考公真题 AI分析 微信推送
- 从华图教育爬取每日一练（失败则AI生成模拟题）
- DeepSeek分析：解析+答案+知识点
- Server酱推送到微信
"""
import os
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime

# 配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-v4-pro"
SERVERCHAN_KEY = os.environ.get("SERVERCHAN_KEY", "")

def call_llm(prompt, system="你是一位资深的公务员考试辅导老师，擅长行测和申论。"):
    """调用DeepSeek API"""
    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 2000
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {DEEPSEEK_API_KEY}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]

def fetch_question_from_web():
    """尝试从华图教育爬取每日一练"""
    try:
        url = "https://www.huatu.com/news/lianxi/"
        req = urllib.request.Request(url, method="GET")
        req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        # 提取题目链接
        links = re.findall(r'href="(https?://www\.huatu\.com/[^"]*\d{4}[^"]*)"[^>]*>([^<]*(?:练习|真题|每日|行测|申论)[^<]*)</a>', html)
        if links:
            # 访问第一个链接获取题目
            article_url, title = links[0]
            req2 = urllib.request.Request(article_url, method="GET")
            req2.add_header("User-Agent", "Mozilla/5.0")
            with urllib.request.urlopen(req2, timeout=15) as resp2:
                article_html = resp2.read().decode("utf-8", errors="ignore")
            # 提取正文
            content_match = re.search(r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>', article_html, re.DOTALL)
            if content_match:
                content = re.sub(r'<[^>]+>', '\n', content_match.group(1))
                content = re.sub(r'\n{3,}', '\n\n', content).strip()
                if len(content) > 50:
                    return title.strip(), content[:3000]
        return None, None
    except Exception as e:
        print(f"[爬取失败] {e}")
        return None, None

def generate_question():
    """AI生成一道考公模拟题"""
    subjects = [
        "言语理解与表达", "数量关系", "判断推理", "资料分析", "常识判断",
        "申论：归纳概括", "申论：提出对策", "申论：综合分析"
    ]
    import random
    subject = random.choice(subjects)
    
    prompt = f"""请出一道{subject}的公务员考试真题级别的模拟题。要求：
1. 题目难度接近真实考试
2. 如果是行测题，给出A/B/C/D四个选项
3. 如果是申论题，给出材料和要求
4. 只出题目，不要给答案和解析

格式：
【题目】{subject}
[题目内容]"""
    
    question = call_llm(prompt)
    return f"AI模拟题 - {subject}", question

def analyze_question(title, question):
    """用DeepSeek分析题目"""
    prompt = f"""请分析以下公务员考试题目，给出详细的解析：

{question}

请按以下格式输出：
【参考答案】给出正确答案
【解析】详细解释为什么选这个答案，其他选项为什么不对
【知识点】这道题考查的核心知识点（1-2句话）
【备考建议】针对这个知识点的备考建议（1句话）"""
    
    return call_llm(prompt)

def push_to_wechat(title, content):
    """通过Server酱推送到微信"""
    if not SERVERCHAN_KEY:
        print("[推送] SERVERCHAN_KEY未配置，跳过推送")
        print(f"\n标题: {title}")
        print(f"\n内容:\n{content[:500]}")
        return False
    
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
    data = urllib.parse.urlencode({
        "title": title,
        "desp": content
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    if result.get("code") == 0:
        print(f"[推送成功] {title}")
        return True
    else:
        print(f"[推送失败] {result}")
        return False

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"=== 每日考公真题 {today} ===")
    
    # 1. 获取题目
    print("[步骤1] 获取题目...")
    title, question = fetch_question_from_web()
    source = "华图教育"
    
    if not question:
        print("[步骤1] 爬取失败，使用AI生成模拟题")
        title, question = generate_question()
        source = "AI模拟"
    
    print(f"[步骤1] 题目来源: {source}")
    print(f"[步骤1] 标题: {title}")
    
    # 2. 分析题目
    print("[步骤2] AI分析中...")
    analysis = analyze_question(title, question)
    print("[步骤2] 分析完成")
    
    # 3. 组装内容
    content = f"""## 📝 每日考公真题 ({today})

**来源**: {source}

---

### {title}

{question}

---

### 📖 AI解析

{analysis}

---

> 每天进步一点，上岸不是梦。
> Powered by DeepSeek V4 Pro | [GitHub](https://github.com/Equinox7379/gongkao-daily)
"""
    
    # 4. 推送
    print("[步骤3] 推送到微信...")
    push_to_wechat(f"考公每日一题 {today}", content)
    
    # 5. 保存到文件（GitHub Actions会自动commit）
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/{today}.md", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[步骤4] 已保存到 output/{today}.md")

if __name__ == "__main__":
    main()
