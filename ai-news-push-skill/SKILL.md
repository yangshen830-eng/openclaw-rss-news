---
name: AI新闻推送
description: 每天自动抓取AI/科技领域热门新闻，整理成markdown文档并推送给用户
emoji: 🤖
metadata:
  clawdbot:
    emoji: 🤖
    requires:
      bins: ["blogwatcher", "curl"]
    install:
      - id: blogwatcher
        kind: go
        module: github.com/Hyaxia/blogwatcher/cmd/blogwatcher@latest
        label: Install blogwatcher
    config:
      - key: news_dir
        description: 新闻保存目录
        default: ~/ai-news/
      - key: max_news
        description: 每日新闻条数
        default: "10"
      - key: feeds
        description: RSS订阅源列表（逗号分隔）
        default: "https://news.ycombinator.com/rss,https://openai.com/blog/rss.xml,https://36kr.com/newsflashes,https://www.technologyreview.com/feed/"
---

# AI新闻推送

每天抓取 AI/科技领域新闻，整理成 markdown 文档。

## 功能

- 自动抓取多个 RSS 源
- 解析并筛选重要新闻
- 整理成中文摘要
- 按日期保存为 .md 文件

## 使用方法

```bash
# 手动运行新闻抓取
ai-news-push

# 查看今日新闻
cat ~/ai-news/$(date +%Y-%m-%d)-news.md
```

## RSS 源配置

默认源：
- Hacker News
- OpenAI Blog
- 36kr
- MIT Tech Review

可修改 skill 配置添加更多源。
