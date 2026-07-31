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
# ---------- 历史记忆（仓库 data/maimemo_history.json，让云端记得过去） ----------
HISTORY = "data/maimemo_history.json"

def load_history():
    try:
        with open(HISTORY, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_history(history):
    import os as _os
    _os.makedirs(_os.path.dirname(HISTORY), exist_ok=True)
    with open(HISTORY, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=1)

def streak_info(history, today):
    """从历史算连续零进度天数 + 最后一次有进度的日期"""
    zero_streak = 0
    last_active = None
    dates = sorted(history.keys(), reverse=True)
    for d in dates:
        if d >= today:
            continue
        if history[d].get("finished", 0) > 0:
            last_active = d
            break
        zero_streak += 1
    return zero_streak, last_active

# ---------- DeepSeek 生成文案（风格：锋利/考据/对质/猫系，德冥 08-01 定） ----------
STYLE_SYSTEM = (
    "你是德冥的陪学助手小A，风格要求：锋利、考据、对质式（直接戳穿借口）、零套话、猫系（爱用喵）。"
    "会用数据说话，会翻历史记录扎心，不哄人。生成中文文案，长度中等。"
)

def gen_progress_text(cfg, finished, total, minutes, remind, zero_streak, last_active, today):
    if remind and zero_streak >= 1:
        streak_txt = f"已经连续 {zero_streak + 1} 天零进度（含今天）" if zero_streak >= 1 else ""
        last_txt = f"上一次背词是 {last_active}。"
        user = (
            f"今天是 {today}，墨墨进度：{finished}/{total} 词，学习时长 {minutes} 分钟。\n"
            f"历史记录：{last_txt} 连续零进度天数（含今天）≈ {zero_streak + 1}。\n"
            "请生成一条晚间催促提醒，要求：①开头猫emoji+直呼德冥 ②列今日刺眼数据 "
            "③翻历史扎心（连续零进度、上次背词是什么时候）④点出后果（考公词库背不完）"
            "⑤给明确行动指令（现在打开墨墨，哪怕10个）⑥结尾喵。参考语气示例："
            "\"一个词都没背。我翻了记录——之后连续零进度已经成了常态。你知道这意味着什么吗？"
            "不是今天忘了，是你压根没打开过这个app。现在，立刻，打开墨墨背单词。哪怕只背10个也比0强。别等我明天再来报这个0了。喵。\""
        )
    else:
        user = (
            f"今天是 {today}，墨墨进度：{finished}/{total} 词，学习时长 {minutes} 分钟。\n"
            "请生成一条{'简短进度播报' if not remind else '温和提醒'}：数据+一句评价，"
            "未完成就催一下（用猫系语气），完成就夸。不要太长。"
        )
    try:
        return deepseek(cfg, STYLE_SYSTEM, user)
    except Exception:
        return None  # fallback 到简单文案

def mode_progress(cfg, remind=False):
    d = maimemo(cfg, "/study/get_study_progress", {})
    p = d["data"]["progress"]
    finished, total = p["finished"], p["total"]
    minutes = p.get("study_time", 0) // 60000
    today = time.strftime("%Y-%m-%d")
    history = load_history()
    zero_streak, last_active = streak_info(history, today)
    title = f"墨墨{'晚间' if remind else '每日'}进度：{finished}/{total}"
    text = gen_progress_text(cfg, finished, total, minutes, remind, zero_streak, last_active, today)
    if text is None:
        lines = [f"今日完成 {finished}/{total} 词，学习 {minutes} 分钟。"]
        if finished < total:
            lines.append("还没背完，现在去背还来得及。" if remind else "加油，把剩下的背完！")
        else:
            lines.append("今日全勤，干得好！")
        text = "\n".join(lines)
    push(cfg, title, text)
    # 记录当天最终状态（晚间/遗忘词时点写历史，早报只读不写避免污染）
    if remind:
        history[today] = {"finished": finished, "total": total, "study_time": minutes * 60000}
        save_history(history)

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
