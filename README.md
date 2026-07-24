# 每日AI早报 微信推送

零成本、全自动的AI每日早报推送系统。GitHub Actions 定时运行，Hacker News + GitHub Trending 数据源，DeepSeek 总结，Server酱推送到微信。

## 工作流程

```
每天8:00 → GitHub Actions触发 →
  1. Hacker News API 获取今日AI热门故事
  2. GitHub API 获取今日新热门AI项目
  3. DeepSeek总结成中文早报
  4. Server酱推送到微信
  5. 早报归档到output/目录
```

## 配置步骤

### 1. Fork 本仓库

### 2. 注册 Server酱
- 访问 https://sct.ftqq.com
- 微信扫码登录
- 获取 **SENDKEY**

### 3. 获取 DeepSeek API Key
- 访问 https://platform.deepseek.com
- 创建 API Key

### 4. 配置 GitHub Secrets
仓库 Settings → Secrets and variables → Actions → New repository secret：
- `DEEPSEEK_API_KEY` — DeepSeek的API密钥
- `SERVERCHAN_KEY` — Server酱的SENDKEY

### 5. 手动测试
Actions → "每日AI早报推送" → Run workflow

## 早报内容

每天推送包含：
- **今日AI大事件** — 从Hacker News筛选AI相关热门故事，DeepSeek中文概括
- **GitHub新星** — 当日新创建的高star AI项目，一句话说明为什么值得关注
- **一句话点评** — AI动态趋势总结

## 技术栈

- Python 3.11 + urllib（零依赖）
- Hacker News API（免费公开）
- GitHub Search API（免费公开）
- DeepSeek V4 Pro（LLM总结）
- Server酱（微信推送）
- GitHub Actions（定时运行，零成本）

## License

MIT
