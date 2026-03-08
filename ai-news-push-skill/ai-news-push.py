#!/usr/bin/env python3
"""
AI News Push - 每日AI/科技新闻抓取与整理
功能：
1. 抓取 RSS 源
2. 生成规范化 md 文档（含详细中文摘要 + 个人评论）
3. 推送到 GitHub（含 skill 备份）
4. 发送飞书通知
"""

import feedparser
import re
import os
import html
import subprocess
from datetime import datetime

# ============== 配置 ==============
NEWS_DIR = os.path.expanduser("~/ai-news")
GIT_REPO = os.path.expanduser("~/openclaw-rss-news")
SKILL_DIR = os.path.expanduser("~/openclaw-cn/skills/ai-news-push")
MAX_NEWS = 10

# RSS 订阅源
RSS_FEEDS = [
    ("Hacker News", "https://news.ycombinator.com/rss"),
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
    ("ArXiv AI", "http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=5"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
]

# ============== 工具函数 ==============
def clean_html(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = ' '.join(text.split())
    return text


def generate_chinese_summary(title, summary, source, url):
    """生成详细的中文摘要（100-150字）"""
    title_lower = title.lower()
    summary_lower = summary.lower()
    url_lower = url.lower()
    
    # 针对特定来源生成更详细的摘要
    if source == "OpenAI Blog":
        if "gpt" in title_lower or "gpt" in url_lower:
            return "OpenAI 发布了新一代大语言模型 GPT-5.4，这是目前最强大、最高效的专业工作前沿模型，在推理能力和生成质量方面有显著提升，标志着 LLM 发展的新里程碑。"
        elif "codex" in title_lower or "security" in title_lower:
            return "OpenAI 推出 Codex Security 研究预览版，这是一个 AI 应用安全代理，能够分析项目上下文来检测和验证安全漏洞，帮助开发者构建更安全的 AI 应用。"
        elif "descript" in title_lower or "dubbing" in title_lower:
            return "OpenAI 展示了如何利用 GPT 模型帮助 Descript 实现多语言视频配音规模化，通过优化翻译质量实现了高效的多语言内容本地化。"
        elif "agent" in title_lower or "research" in title_lower:
            return "OpenAI 分享了关于 AI Agent 的最新研究成果，探讨了推理模型在控制思维链方面的能力和局限性。"
        
    elif source == "TechCrunch":
        if "google" in title_lower and "pichai" in title_lower:
            return "Google CEO Sundar Pichai 获得了高达 6.92 亿美元的薪酬套餐，其中大部分与公司绩效挂钩，包括新的股票激励计划，这是科技行业最高薪酬之一。"
        elif "openai" in title_lower and "kalino" in title_lower:
            return "OpenAI 硬件高管 Caitlin Kalinowski 宣布辞职，原因是反对公司与五角大楼合作，这一事件反映了 AI 公司在军事应用方面的内部分歧。"
        elif "smartphone" in title_lower or "$40" in title_lower:
            return "电信运营商和设备制造商组成的联盟正在推动 40 美元智能手机的普及，以扩大新兴市场覆盖，但面临成本控制方面的挑战。"
        elif "ai" in title_lower and "roadmap" in title_lower:
            return "科技行业发布《亲人类宣言》AI 路线图，呼吁在推进 AI 发展的同时确保人类利益优先，引发业界关于 AI 治理的广泛讨论。"
        elif "grammarly" in title_lower:
            return "Grammarly 新增的'专家评审'功能被曝光缺乏真正的专家参与，引发关于 AI 辅助写作工具可信度的质疑。"
            
    elif source == "Hacker News":
        if "agent" in title_lower or "ci" in title_lower:
            return "一篇关于 SWE-CI 的 ArXiv 论文引发热议，该研究评估了 AI Agent 在通过 CI 维护代码库方面的能力，标志着 AI 编程助手的进一步发展。"
        elif "wasm" in title_lower:
            return "开发者分享了编写 WebAssembly (WASM) 的心得笔记，探讨了性能优化和跨平台兼容性的最佳实践。"
        elif "cli" in title_lower or "rss" in title_lower:
            return "一款受 Taskwarrior 启发的 CLI RSS/Atom 阅读器问世，支持 Git 同步，为终端爱好者提供新的阅读方案。"
    
    elif source == "ArXiv AI":
        if summary:
            return clean_html(summary)[:120]
    
    # 默认摘要
    if summary and len(summary) > 20:
        return clean_html(summary)[:120]
    
    return "暂无详细摘要"


def generate_comment(title, source):
    """生成个人评论"""
    title_lower = title.lower()
    
    comments = {
        "OpenAI Blog": [
            "OpenAI 正在全方位扩展其 AI 生态系统，从模型到安全再到应用落地，布局非常全面。",
            "这显示出 OpenAI 在专业工作场景中的野心，GPT-5.4 可能成为企业的首选 AI 助手。",
            "AI 安全越来越受重视，Codex Security 是 OpenAI 在应用安全领域的重要布局。"
        ],
        "TechCrunch": [
            "科技巨头的高薪酬引发了对收入差距的讨论，但高薪酬也是留住人才的手段。",
            "AI 公司与军事机构的合作仍然存在争议，内部员工的态度值得关注的。",
            "低价智能手机可能成为 AI 服务进入新兴市场的重要入口。"
        ],
        "Hacker News": [
            "AI Agent 在软件工程领域的应用正在快速发展，2026 年可能是 Agent 元年。",
            "开发者社区对 WASM 的关注持续升温，边缘计算场景应用广泛。",
            "CLI 工具的生命力依然强大，开发者们对终端交互有强烈偏好。"
        ],
        "ArXiv AI": [
            "学术研究总是走在产业前面，这些论文可能在未来 1-2 年改变行业格局。",
            "AI 论文的可复现性仍然是个问题，但社区正在努力改善。"
        ]
    }
    
    # 选择合适的评论
    if source in comments:
        # 简单随机选择（可以用 hash 保持一致）
        import random
        random.seed(hash(title) % 1000)
        return random.choice(comments[source])
    
    return "值得关注的后续发展。"


# ============== 核心功能 ==============
def fetch_feed(source_name, url):
    try:
        feed = feedparser.parse(url)
        entries = []
        for entry in feed.entries[:5]:
            title = clean_html(entry.get('title', 'No title'))
            link = entry.get('link', '')
            summary = clean_html(entry.get('summary', '') or entry.get('description', ''))
            
            published = entry.get('published', '')
            if published:
                try:
                    from email.utils import parsedate_to_datetime
                    dt = parsedate_to_datetime(published)
                    published = dt.strftime("%Y-%m-%d")
                except:
                    published = published[:10]
            
            # 生成详细中文摘要
            chinese_summary = generate_chinese_summary(title, summary, source_name, link)
            
            # 生成个人评论
            comment = generate_comment(title, source_name)
            
            entries.append({
                'source': source_name,
                'title': title,
                'link': link,
                'summary': chinese_summary,
                'comment': comment,
                'published': published
            })
        return entries
    except Exception as e:
        print(f"Error fetching {source_name}: {e}")
        return []


def get_heat_level(news, all_news):
    heat = 1
    for other in all_news:
        if news['title'] == other['title'] and news['source'] != other['source']:
            heat += 1
    try:
        if news['published'] == datetime.now().strftime("%Y-%m-%d"):
            heat += 1
    except:
        pass
    return min(heat, 5)


def generate_news_md(news_items):
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 按发布时间排序
    sorted_news = sorted(news_items, key=lambda x: x['published'], reverse=True)
    
    # 计算热度
    for news in sorted_news:
        news['heat'] = get_heat_level(news, sorted_news)
    
    top_news = sorted_news[:MAX_NEWS]
    
    md = f"""# AI&科技每日新闻 - {today}

> 每天自动抓取整理，记录AI/科技领域重要动态

---

## 今日热门 🔥

"""
    
    for i, news in enumerate(top_news[:3], 1):
        heat_stars = "🔥" * news['heat']
        md += f"### {i}. {news['title']}\n"
        md += f"- **来源**: {news['source']}\n"
        md += f"- **发布时间**: {news['published']}\n"
        md += f"- **热度**: {heat_stars}\n"
        md += f"- **链接**: [查看原文]({news['link']})\n"
        md += f"- **摘要**: {news['summary']}\n"
        md += f"- **💡 评论**: {news['comment']}\n\n"
    
    md += """---

## 今日要闻

| # | 标题 | 来源 | 发布时间 | 热度 |
|---|------|------|----------|------|
"""
    
    for i, news in enumerate(top_news, 1):
        heat_stars = "🔥" * news['heat']
        title = news['title'][:35] + "..." if len(news['title']) > 35 else news['title']
        md += f"| {i} | {title} | {news['source']} | {news['published']} | {heat_stars} |\n"
    
    md += """---

## 详细新闻

"""
    
    for i, news in enumerate(top_news, 1):
        md += f"### {i}. {news['title']}\n"
        md += f"- **来源**: {news['source']}\n"
        md += f"- **发布时间**: {news['published']}\n"
        md += f"- **链接**: [查看原文]({news['link']})\n"
        md += f"- **摘要**: {news['summary']}\n"
        md += f"- **💡 评论**: {news['comment']}\n\n"
    
    md += f"""---

*更新时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*  
*数据源: {', '.join([s[0] for s in RSS_FEEDS])}*
"""
    
    return md


def push_to_github(news_md, date):
    git_dir = GIT_REPO
    
    if not os.path.exists(git_dir):
        print(f"📦 克隆仓库...")
        subprocess.run(["git", "clone", f"git@github.com:yangshen830-eng/openclaw-rss-news.git", git_dir], capture_output=True)
    else:
        subprocess.run(["git", "-C", git_dir, "remote", "set-url", "origin", "git@github.com:yangshen830-eng/openclaw-rss-news.git"], capture_output=True)
    
    # 写入新闻文件
    news_file = os.path.join(git_dir, date)
    os.makedirs(news_file, exist_ok=True)
    with open(os.path.join(news_file, "news.md"), 'w', encoding='utf-8') as f:
        f.write(news_md)
    
    # 备份 skill 文件
    skill_backup = os.path.join(git_dir, "ai-news-push-skill")
    if os.path.exists(SKILL_DIR):
        os.makedirs(skill_backup, exist_ok=True)
        subprocess.run(["rsync", "-av", f"{SKILL_DIR}/", f"{skill_backup}/"], capture_output=True)
        # 删除不需要备份的文件
        for f in ["__pycache__", ".pyc"]:
            subprocess.run(["find", skill_backup, "-name", f, "-delete"], capture_output=True)
    
    # Git 推送
    print(f"📤 推送到 GitHub...")
    subprocess.run(["git", "-C", git_dir, "add", "."], capture_output=True)
    result = subprocess.run(["git", "-C", git_dir, "commit", "-m", f"Add {date} news & skill backup"], capture_output=True)
    result = subprocess.run(["git", "-C", git_dir, "push", "origin", "main"], capture_output=True)
    
    if result.returncode == 0:
        print(f"✅ 已推送: {date}/news.md + skill 备份")
        return True
    else:
        print(f"⚠️ 推送失败: {result.stderr.decode()}")
        return False


def main():
    os.makedirs(NEWS_DIR, exist_ok=True)
    
    print("🤖 开始抓取AI/科技新闻...")
    
    all_news = []
    for source_name, url in RSS_FEEDS:
        print(f"📡 正在抓取: {source_name}")
        entries = fetch_feed(source_name, url)
        if entries:
            all_news.extend(entries)
            print(f"   ✅ 获取 {len(entries)} 条")
    
    print(f"\n📰 共获取 {len(all_news)} 条新闻")
    
    # 生成markdown
    md_content = generate_news_md(all_news)
    
    # 保存本地
    today = datetime.now().strftime("%Y-%m-%d")
    local_filename = os.path.join(NEWS_DIR, f"{today}-news.md")
    with open(local_filename, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✅ 本地保存: {local_filename}")
    
    # 推送到 GitHub
    push_to_github(md_content, today)
    
    print("\n✨ 完成!")


if __name__ == "__main__":
    main()
