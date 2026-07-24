# 每日考公真题 AI分析 微信推送

零成本、全自动的考公每日一题推送系统。GitHub Actions 定时运行，DeepSeek 分析，Server酱推送到微信。

## 工作流程

```
每天8:00 → GitHub Actions触发 → 爬取华图每日一练(失败则AI生成) → DeepSeek分析 → Server酱推送到微信
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
在你的仓库 Settings → Secrets and variables → Actions → New repository secret：
- `DEEPSEEK_API_KEY` — DeepSeek的API密钥
- `SERVERCHAN_KEY` — Server酱的SENDKEY

### 5. 手动测试
Actions → "每日考公真题推送" → Run workflow

## 功能

- **多数据源**：优先从华图教育爬取每日一练，爬取失败自动切换AI生成
- **AI深度分析**：参考答案 + 详细解析 + 知识点 + 备考建议
- **微信推送**：每天早上8:00自动推送到微信
- **历史归档**：每天题目保存到 output/ 目录，自动commit到仓库
- **零成本**：GitHub Actions 免费2000分钟/月��足够每天跑一次

## 技术栈

- Python 3.11 + urllib（零依赖，不用装额外包）
- DeepSeek V4 Pro（LLM分析）
- Server酱（微信推送）
- GitHub Actions（定时运行）

## License

MIT
