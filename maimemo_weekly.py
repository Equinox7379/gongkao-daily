# -*- coding: utf-8 -*-
"""墨墨数据周报 - 拉取学习数据+生成报告+Server酱推送"""
import os, json, urllib.request, urllib.parse
from datetime import datetime

MAIMEMO_TOKEN = os.environ.get("MAIMEMO_TOKEN", "")
SERVERCHAN_KEY = os.environ.get("SERVERCHAN_KEY", "")

def maimemo_post(path, body=None):
    url = f"https://open.maimemo.com/open/api/v1{path}"
    data = json.dumps(body or {}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {MAIMEMO_TOKEN}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def push(title, content):
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
    data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"推送: {json.loads(resp.read().decode('utf-8')).get('code')}")

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 获取今日进度
    progress = maimemo_post("/study/get_study_progress")
    p = progress.get("data", {}).get("progress", {})
    finished = p.get("finished", 0)
    total = p.get("total", 0)
    
    # 获取词本
    notepad_resp = maimemo_post("/study/query_study_records", {"spellings": ["hatred", "compromise", "consistent"], "as_count": False, "limit": 10})
    records = notepad_resp.get("data", {}).get("records", [])
    
    forget_count = sum(1 for r in records if r.get("last_response") == "FORGET")
    
    content = f"""## 📊 墨墨数据周报 ({today})

### 本周学习概况

| 指标 | 数值 |
|------|------|
| 今日完成 | {finished}/{total} |
| 抽查遗忘词 | {forget_count}/{len(records)} |
| 遗忘率 | {forget_count*100//max(len(records),1)}% |

### 抽查词状态

"""
    for r in records:
        status = "❌遗忘" if r.get("last_response") == "FORGET" else "✅熟悉"
        content += f"- **{r.get('voc_spelling', '?')}**: {status} (复习{r.get('study_count', 0)}次)\n"
    
    content += f"""

---

> 📚 坚持背单词，上岸可期
> [墨墨管理命令手册](https://github.com/Equinox7379/yongji-knowledge-vault)"""
    
    push(f"📊 墨墨周报 {today}", content)
    print(f"完成: {today}")

if __name__ == "__main__":
    main()
