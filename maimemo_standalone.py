#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""墨墨背单词独立自动化（2026-07-31 迁移，与 WorkBuddy 解耦）
用法: python maimemo_standalone.py <mode>
mode: progress | remind | track | analyze
密钥读自 ~/.workbuddy/maimemo_standalone_config.json（不硬编码）"""
import json
import os
import sys
import time
import urllib.request

HOME = os.path.expanduser("~")
CFG_PATH = os.path.join(HOME, ".workbuddy", "maimemo_standalone_config.json")
MAIMEMO = "https://open.maimemo.com/open/api/v1"
DEEPSEEK = "https://api.deepseek.com/chat/completions"

def load_cfg():
    """密钥来源：环境变量优先（GitHub Actions Secrets），fallback 本地配置文件"""
    def env_or(key):
        return os.environ.get(key) or None
    cfg = {}
    try:
        with open(CFG_PATH, encoding="utf-8") as f:
            file_cfg = json.load(f)
    except Exception:
        file_cfg = {}
    cfg["maimemo_token"] = env_or("MAIMEMO_TOKEN") or file_cfg.get("maimemo_token")
    cfg["deepseek_key"] = env_or("DEEPSEEK_API_KEY") or file_cfg.get("deepseek_key")
    cfg["sendkey"] = env_or("SERVERCHAN_KEY") or file_cfg.get("sendkey")
    cfg["deepseek_model"] = env_or("DEEPSEEK_MODEL") or file_cfg.get("deepseek_model") or "deepseek-chat"
    return cfg

def maimemo(cfg, path, body=None, method=None):
    url = MAIMEMO + path
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method or ("POST" if body is not None else "GET"))
    req.add_header("Authorization", "Bearer " + cfg["maimemo_token"])
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def deepseek(cfg, system, user):
    req = urllib.request.Request(DEEPSEEK, data=json.dumps({
        "model": cfg.get("deepseek_model", "deepseek-chat"),
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.7,
    }).encode("utf-8"), method="POST")
    req.add_header("Authorization", "Bearer " + cfg["deepseek_key"])
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]

def push(cfg, title, content):
    sendkey = cfg.get("sendkey")
    if not sendkey:
        print(f"[未配置方糖 SendKey，仅打印]\n{title}\n{content}", flush=True)
        return
    import urllib.parse
    url = f"https://sctapi.ftqq.com/{sendkey}.send?" + urllib.parse.urlencode(
        {"title": title, "desp": content})
    urllib.request.urlopen(urllib.request.Request(url), timeout=15).read()

# ---------- 四个任务 ----------
def mode_progress(cfg, remind=False):
    d = maimemo(cfg, "/study/get_study_progress", {})
    p = d["data"]["progress"]
    finished, total = p["finished"], p["total"]
    minutes = p.get("study_time", 0) // 60000
    title = f"墨墨{'晚间' if remind else '每日'}进度：{finished}/{total}"
    lines = [f"今日完成 {finished}/{total} 词，学习 {minutes} 分钟。"]
    if finished < total:
        lines.append("还没背完，现在去背还来得及。" if remind else "加油，把剩下的背完！")
    else:
        lines.append("今日全勤，干得好！")
    push(cfg, title, "\n".join(lines))

def mode_track(cfg):
    items = maimemo(cfg, "/study/get_today_items", {"limit": 500})["data"]
    forget = [i for i in items if i.get("last_response") == "FORGET"]
    if not forget:
        push(cfg, "墨墨遗忘词：今日全记住", "今天全部记住，没有遗忘词，干得好！")
        return
    q = maimemo(cfg, "/vocabulary/query", {"spellings": [i["spelling"] for i in forget]})
    voc_map = {v["spelling"]: v["id"] for v in q.get("data", {}).get("voc", [])}
    # DeepSeek 批量生成助记
    words = list(voc_map.keys())[:20]
    if words:
        sys_prompt = "你为背单词用户生成中文助记。要求：词根/谐音/联想混用，怎么好记怎么来，输出 JSON 数组，每项 {spelling, note_type(中文如\"词根\"/\"谐音\"/\"联想\"), note(助记内容)}，保持简短。"
        try:
            raw = deepseek(cfg, sys_prompt, "为这些词生成助记：" + "、".join(words))
            import re
            arr = json.loads(re.search(r"\[.*\]", raw, re.S).group(0))
            wrote = 0
            for item in arr[:20]:
                vid = voc_map.get(item["spelling"])
                if not vid:
                    continue
                maimemo(cfg, "/notes", {"note": {"voc_id": vid, "note_type": item["note_type"], "note": item["note"]}})
                wrote += 1
                time.sleep(0.5)
        except Exception as e:
            push(cfg, "墨墨遗忘词：助记生成失败", f"错误: {e}")
            return
        push(cfg, f"墨墨遗忘词：{len(forget)} 个", f"今日 {len(forget)} 个遗忘词，已为 {wrote} 个生成助记写入墨墨。")
    else:
        push(cfg, f"墨墨遗忘词：{len(forget)} 个", "遗忘词已记录，助记生成跳过（词表匹配为空）。")

def mode_analyze(cfg):
    notes = maimemo(cfg, "/notepads")["data"]
    nid = None
    for n in notes:
        if n.get("title") == "每日不熟":
            nid = n["id"]
            break
    if not nid:
        push(cfg, "墨墨周分析", "找不到\"每日不熟\"词本。")
        return
    note = maimemo(cfg, f"/notepads/{nid}")["data"]
    words = [w["spelling"] for w in note.get("words", [])][:755]
    records = []
    for i in range(0, len(words), 200):
        rec = maimemo(cfg, "/study/query_study_records", {"spellings": words[i:i+200]})
        records.extend(rec.get("data", []))
        time.sleep(0.5)
    # 统计：按复习次数分组遗忘率
    groups = {"1-5": [0, 0], "6-10": [0, 0], "11-15": [0, 0], "16-20": [0, 0], "20+": [0, 0]}
    for r in records:
        n = r.get("review_count", 0)
        key = "1-5" if n <= 5 else "6-10" if n <= 10 else "11-15" if n <= 15 else "16-20" if n <= 20 else "20+"
        groups[key][0] += 1
        if r.get("last_response") == "FORGET":
            groups[key][1] += 1
    summary = "\n".join(f"{k} 次: {v[0]}词 遗忘{v[1]} ({v[1]/v[0]*100:.0f}%)" if v[0] else f"{k} 次: 无" for k, v in groups.items())
    report_path = os.path.join(HOME, "chatgpt大人专用库", "02-学习与考公", "英语", "墨墨学习曲线分析.md")
    try:
        sys_prompt = "你是学习数据分析助手，输出简洁的中文周报，含：遗忘率趋势判断、顽固词提醒、下周建议。不要客套。"
        ai = deepseek(cfg, sys_prompt, f"以下按复习次数分组的遗忘统计：\n{summary}")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# 墨墨学习曲线分析（周报）\n\n{ai}\n\n## 原始统计\n\n{summary}\n")
        push(cfg, "墨墨每周分析完成", f"报告已写入 {report_path}\n\n{summary[:200]}...")
    except Exception as e:
        push(cfg, "墨墨周分析失败", f"错误: {e}")

def main():
    cfg = load_cfg()
    mode = sys.argv[1] if len(sys.argv) > 1 else "progress"
    if mode == "progress":
        mode_progress(cfg, False)
    elif mode == "remind":
        mode_progress(cfg, True)
    elif mode == "track":
        mode_track(cfg)
    elif mode == "analyze":
        mode_analyze(cfg)
    else:
        print("未知模式: " + mode)

if __name__ == "__main__":
    main()
