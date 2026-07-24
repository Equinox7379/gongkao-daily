# -*- coding: utf-8 -*-
"""哲学每日金句 - 从预设列表随机选一条+Server酱推送"""
import os, json, urllib.request, urllib.parse, random
from datetime import datetime

SERVERCHAN_KEY = os.environ.get("SERVERCHAN_KEY", "")

QUOTES = [
    ("就算整片卡拉迪亚都是假的，我决定爱你这件事，是真的不能再真了。", "科林", "鲁永吉传-科林篇"),
    ("本质不underlying存在作为基础，而是immanent于存在。", "霍尔盖特", "本质论中对基础主义的批判"),
    ("矛盾是一切运动和生命力的根。", "黑格尔", "逻辑学"),
    ("不缝意义，让过剩快感甩出主体性。", "德冥", "个人随笔"),
    ("没有神，但是有奇迹。", "未明子", "如何成为历史的一部分"),
    ("辩证法不是正反合——它是一种让概念自己说话的分析方法。", "霍尔盖特", "黑格尔导论"),
    ("信任不是盲目相信，也不是验证后的结论——信任是对自由已实现于世界的感知性认识。", "霍尔盖特", "权利与信任"),
    ("否定性的最高形式不是实施而是悬置——力量在克制中才成为可占有的力量。", "Anthrax分析", "Underground"),
    ("真正的自由不是任意选择，而是理性地自我规定。", "黑格尔", "法哲学原理"),
    ("混序=混沌与秩序的辩证统一——最有效的系统既不是纯混沌也不是纯有序。", "迪伊·霍克", "混序"),
    ("扬弃不是否定后消失，而是否定后保存有价值的内容并提升到更高层次。", "黑格尔", "逻辑学"),
    ("法律威慑失败了——他们听到的不是'别黑'，而是'别被抓'。", "Dreyfus", "Underground"),
]

def push(title, content):
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
    data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        print(f"推送: {json.loads(resp.read().decode('utf-8')).get('code')}")

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    quote, author, source = random.choice(QUOTES)
    
    content = f"""## 🌅 哲学每日金句 ({today})

> *"{quote}"*
> — **{author}**，《{source}》

---

> 💭 每天一个想法，积少成多。
> [知识库](https://github.com/Equinox7379/yongji-knowledge-vault) | [博客](https://equinox7379.github.io/jekyll-now/)"""
    
    push(f"🌅 哲学金句 {today}", content)
    print(f"完成: {today} - {author}")

if __name__ == "__main__":
    main()
