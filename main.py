# -*- coding: utf-8 -*-
"""
每日AI早报 微信推送
- Hacker News API 获取今日Top故事（筛选AI相关）
- GitHub API 获取今日热门AI项目
- DeepSeek总结成中文早报
- Server酱推送到微���
"""
import os
import json
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-v4-pro"
SERVERCHAN_KEY = os.environ.get("SERVERCHAN_KEY", "")

AI_KEYWORDS = ["ai", "llm", "gpt", "ml", "model", "agent", "neural", "transformer",
               "openai", "anthropic", "claude", "gemini", "diffusion", "rag",
               "embedding", "fine-tun", "training", "inference", "quantiz",
               "language model", "machine learning", "deep learning", "computer vision",
               "generative", "multimodal", "robot", "autonomous", "chip", "gpu",
               "nvidia", "tesla", "copilot", "cursor", "coding", "automation"]

def api_get(url, headers=None):
    req = urllib.request.Request(url, method="GET")
    req.add_header("User-Agent", "AI-Daily-Bot/1.0")
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

def fetch_hackernews():
    """从Hacker News获取今日Top AI相关故事"""
    try:
        top_ids = api_get("https://hacker-news.firebaseio.com/v0/topstories.json")[:50]
        stories = []
        for sid in top_ids:
            try:
                item = api_get(f"https://hacker-news.firebaseio.com/v0/item/{sid}.json")
                if item and item.get("type") == "story" and item.get("score", 0) >= 50:
                    title = item.get("title", "").lower()
                    if any(kw in title for kw in AI_KEYWORDS):
                        stories.append({
                            "title": item["title"],
                            "url": item.get("url", f"https://news.ycombinator.com/item?id={sid}"),
                            "score": item["score"],
                            "comments": item.get("descendants", 0)
                        })
            except:
                continue
            if len(stories) >= 10:
                break
        return stories
    except Exception as e:
        print(f"[HN获取失败] {e}")
        return []

def fetch_github_trending():
    """从GitHub获取今日热门AI项目"""
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        url = (f"https://api.github.com/search/repositories"
               f"?q=topic:ai+created:>{yesterday}&sort=stars&order=desc&per_page=10")
        data = api_get(url, headers={"Accept": "application/vnd.github.v3+json"})
        repos = []
        for r in data.get("items", [])[:5]:
            repos.append({
                "name": r["full_name"],
                "desc": r.get("description", "") or "",
                "stars": r["stargazers_count"],
                "url": r["html_url"],
                "language": r.get("language", "") or ""
            })
        return repos
    except Exception as e:
        print(f"[GitHub获取失败] {e}")
        return []

def call_llm(prompt):
    url = f"{DEEPSEEK_BASE_URL}/chat/completions"
    body = json.dumps({
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": "你是一位AI行业分析师，擅长用简洁的中文总结技术动态。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.5,
        "max_tokens": 2000
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {DEEPSEEK_API_KEY}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]

def generate_report(hn_stories, github_repos):
    """用DeepSeek生成中文早报"""
    hn_text = "\n".join(
        f"- {s['title']} (热度:{s['score']}, 评论:{s['comments']})\n  {s['url']}"
        for s in hn_stories
    ) if hn_stories else "今日无AI相关热门故事"

    gh_text = "\n".join(
        f"- {r['name']} (⭐{r['stars']}, {r['language']})\n  {r['desc'][:100]}\n  {r['url']}"
        for r in github_repos
    ) if github_repos else "今日无新热门AI项目"

    prompt = f"""以下是今日AI领域的动态，请用中文生成一份简洁的AI早报。

## Hacker News AI热门
{hn_text}

## GitHub 新热门AI项目
{gh_text}

请按以下格式输出（用Markdown）：

### 今日AI大事件
（挑选3-5条最重要的，用1-2句话中文概括每条的核心内容，附原文链接）

### GitHub新星
（挑选2-3个最值得关注的，用1句话说明它是什么、为什么值得关注）

### 一句话点评
（用一句话总结今天的AI动态趋势）

注意：
- 中文概括，不要直接翻译英文标题
- 突出"为什么重要"，不要只说"发生了什么"
- 保持简洁，总字数控制在800字以内"""

    return call_llm(prompt)

def push_to_wechat(title, content):
    if not SERVERCHAN_KEY:
        print("[推送] SERVERCHAN_KEY未配置")
        print(f"\n{title}\n\n{content[:500]}")
        return False
    url = f"https://sctapi.ftqq.com/{SERVERCHAN_KEY}.send"
    data = urllib.parse.urlencode({"title": title, "desp": content}).encode("utf-8")
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
    print(f"=== 每日AI早报 {today} ===")

    print("[1/4] 获取Hacker News...")
    hn_stories = fetch_hackernews()
    print(f"  获取到 {len(hn_stories)} 条AI相关故事")

    print("[2/4] 获取GitHub热门AI项目...")
    github_repos = fetch_github_trending()
    print(f"  获取到 {len(github_repos)} 个热门项目")

    print("[3/4] DeepSeek生成早报...")
    report = generate_report(hn_stories, github_repos)
    print("  早报生成完���")

    content = f"""## ☀️ 每日AI早报 ({today})

{report}

---

> 数据来源：Hacker News + GitHub Trending
> Powered by DeepSeek V4 Pro
> [GitHub](https://github.com/Equinox7379/gongkao-daily)
"""

    print("[4/4] 推送到微信...")
    push_to_wechat(f"AI早报 {today}", content)

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    with open(f"{output_dir}/{today}.md", "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[完成] 已保存到 output/{today}.md")

if __name__ == "__main__":
    main()
