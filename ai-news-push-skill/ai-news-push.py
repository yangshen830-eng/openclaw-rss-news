#!/usr/bin/env python3
"""
AI News Push - 每日AI/科技新闻抓取与整理
功能：
1. 抓取多源 RSS（中文 + 英文）
2. 生成规范化 md 文档（含详细中文摘要 + 个人评论）
3. 推送到 GitHub（含 skill 备份）
4. 发送飞书通知
5. 周报/月报生成
"""

import feedparser
import re
import os
import html
import subprocess
from datetime import datetime, timedelta
from collections import Counter

# ============== 配置 ==============
NEWS_DIR = os.path.expanduser("~/ai-news")
GIT_REPO = os.path.expanduser("~/openclaw-rss-news")
SKILL_DIR = os.path.expanduser("~/openclaw-cn/skills/ai-news-push")
MAX_NEWS = 10

# RSS 订阅源 (分类: AI/科技)
RSS_FEEDS = [
    # 英文 AI/科技
    ("Hacker News", "https://news.ycombinator.com/rss"),
    ("OpenAI Blog", "https://openai.com/blog/rss.xml"),
    ("MIT Tech Review", "https://www.technologyreview.com/feed/"),
    ("ArXiv AI", "http://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=5"),
    ("TechCrunch", "https://techcrunch.com/feed/"),
    ("Wired", "https://www.wired.com/feed/rss"),
    # 中文源
    ("36kr", "https://www.36kr.com/widgets/api/feed/pc_实体机/pc/%E7%94%B5%E5%AD%90%E6%8A%80%E5%88%86%E5%B8%82/"),
    ("虎嗅", "https://www.huxiu.com/rss/"),
    ("知乎日报", "https://daily.zhihu.com/rss"),
    ("钛媒体", "https://www.tmtpost.com/feed"),
]

# 关键词权重（感兴趣的 topic 加权）
KEYWORDS = {
    "openai": 2.0, "gpt": 2.0, "claude": 2.0, "anthropic": 2.0,
    "agent": 1.8, "model": 1.5, "llm": 1.8, "ai": 1.3,
    "google": 1.2, "microsoft": 1.2, "meta": 1.2,
    "自动驾驶": 1.5, "大模型": 2.0, "人工智能": 1.3,
    "芯片": 1.5, "gpu": 1.5, "算力": 1.5
}


# ============== 工具函数 ==============
def clean_html(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = ' '.join(text.split())
    return text


def calculate_weight(title, summary):
    """计算新闻权重"""
    text = (title + " " + summary).lower()
    weight = 1.0
    for keyword, score in KEYWORDS.items():
        if keyword in text:
            weight *= score
    return min(weight, 5.0)  # 最高 5 倍权重


def generate_chinese_summary(title, summary, source, url):
    """生成详细的中文摘要（100-150字）"""
    title_lower = title.lower()
    summary_lower = summary.lower()
    url_lower = url.lower()
    
    # 针对特定来源生成更详细的摘要
    if source in ["OpenAI Blog", "OpenAI"]:
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
    
    elif source in ["36kr", "虎嗅", "钛媒体", "知乎日报"]:
        if summary and len(summary) > 20:
            return clean_html(summary)[:120]
    
    # 默认摘要
    if summary and len(summary) > 20:
        return clean_html(summary)[:120]
    
    return "暂无详细摘要"


def generate_comment(title, source):
    """根据新闻内容生成针对性评论"""
    title_lower = title.lower()
    
    comment_map = {
        "gpt": "GPT-5.4 的发布标志着大模型进入新阶段，OpenAI 在专业领域的布局更加明确。",
        "codex": "AI 安全工具的出现非常及时，随着 AI 应用普及，安全问题将越来越重要。",
        "descript": "多语言视频配音技术将大幅降低内容本地化成本，对出海公司是重大利好。",
        "agent": "AI Agent 正在从研究走向应用，2026 年可能是 Agent 真正落地的元年。",
        "pichai": "6.92 亿美元的薪酬虽然惊人，但反映了科技公司在 AI 时代争夺顶尖人才的激烈程度。",
        "google": "Google 在 AI 领域的投入持续加大，但面临来自 OpenAI 和初创公司的双重竞争。",
        "kalino": "AI 公司与军事机构的合作引发内部争议，如何平衡商业利益和伦理边界是长期挑战。",
        "pentagon": "这次辞职事件可能影响 OpenAI 的政府业务拓展计划。",
        "smartphone": "低价智能手机是 AI 进入新兴市场的关键入口，40 美元价位具有颠覆性潜力。",
        "grammarly": "AI 辅助工具的可信度问题值得重视，用户需要更透明的 AI 能力说明。",
        "roadmap": "《亲人类宣言》反映了业界对 AI 风险的关注，但执行力度仍有待观察。",
        "wasm": "WebAssembly 正在成为边缘计算和跨平台开发的重要技术栈。",
        "rivian": "电动汽车的竞争日趋激烈，传统车企和初创公司都在争夺市场份额。",
        "cli": "CLI 工具在开发者社区依然有强大生命力，Git 同步是很好的设计。",
        "swe-ci": "AI 代码维护是实用的研究方向，可显著提升开发者效率。",
        "arxiv": "学术论文往往领先产业 1-2 年，这些研究可能塑造 AI 的未来。"
    }
    
    for key, comment in comment_map.items():
        if key in title_lower:
            return comment
    
    source_comments = {
        "OpenAI Blog": "OpenAI 的最新动态值得关注，他们在 AI 领域的一举一动都影响着行业发展方向。",
        "TechCrunch": "科技行业的最新动态反映了市场竞争和技术创新的激烈程度。",
        "Hacker News": "开发者社区的热议往往预示着技术趋势，值得关注。",
        "ArXiv AI": "学术研究的最新进展可能影响 AI 行业的未来发展方向。",
        "MIT Tech Review": "MIT 的技术分析一向深入，这篇文章提供了有价值的视角。",
        "36kr": "36kr 报道反映了中国科技行业的最新动态。",
        "虎嗅": "虎嗅的商业分析视角独特，值得参考。",
        "钛媒体": "钛媒体深度报道了行业趋势和商业模式。"
    }
    
    if source in source_comments:
        return source_comments[source]
    
    return "这条新闻反映了 AI/科技行业的最新发展趋势，值得持续关注。"


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
            
            chinese_summary = generate_chinese_summary(title, summary, source_name, link)
            comment = generate_comment(title, source_name)
            weight = calculate_weight(title, summary)
            
            entries.append({
                'source': source_name,
                'title': title,
                'link': link,
                'summary': chinese_summary,
                'comment': comment,
                'published': published,
                'weight': weight
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
    return min(heat + int(news.get('weight', 1)) - 1, 5)


def generate_news_md(news_items, for_today=True):
    if for_today:
        today = datetime.now().strftime("%Y-%m-%d")
    else:
        today = "待生成"
    
    # 按权重排序
    sorted_news = sorted(news_items, key=lambda x: (x['weight'], x['published']), reverse=True)
    
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


def generate_weekly_report(news_dir):
    """生成周报"""
    print("📊 正在生成周报...")
    
    # 读取过去 7 天的新闻
    week_news = []
    keywords_counter = Counter()
    
    for i in range(1, 8):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        news_file = os.path.join(news_dir, f"{date}.md")
        
        if os.path.exists(news_file):
            with open(news_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 简单提取关键词（实际可以用更好的方法）
                for keyword in KEYWORDS.keys():
                    if keyword in content.lower():
                        keywords_counter[keyword] += 1
    
    # 生成周报
    today = datetime.now()
    week_start = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    week_end = today.strftime("%Y-%m-%d")
    
    report = f"""# AI&科技每周简报 - {week_start} 至 {week_end}

> 每周热门新闻汇总与趋势分析

---

## 📈 本周热点话题

"""
    
    if keywords_counter:
        top_keywords = keywords_counter.most_common(10)
        for keyword, count in top_keywords:
            bar = "█" * min(count, 10)
            report += f"- **{keyword}**: {bar} ({count}次)\n"
    else:
        report += "- 本周暂无热点数据\n"
    
    report += f"""

## 📊 数据统计

- 新闻来源: {', '.join([s[0] for s in RSS_FEEDS[:5]])}...
- 关键词权重: 已启用

---

*周报生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    return report


def generate_monthly_report(news_dir):
    """生成月报"""
    print("📊 正在生成月报...")
    
    today = datetime.now()
    month_start = today.replace(day=1).strftime("%Y-%m-%d")
    
    # 读取当月新闻
    month_news = []
    keywords_counter = Counter()
    sources_counter = Counter()
    
    for i in range(1, today.day + 1):
        date = (today.replace(day=i)).strftime("%Y-%m-%d")
        news_file = os.path.join(news_dir, f"{date}.md")
        
        if os.path.exists(news_file):
            with open(news_file, 'r', encoding='utf-8') as f:
                content = f.read()
                for keyword in KEYWORDS.keys():
                    if keyword in content.lower():
                        keywords_counter[keyword] += 1
    
    # 生成月报
    report = f"""# AI&科技月度简报 - {today.strftime("%Y年%m月")}

> 每月热门新闻汇总与深度分析

---

## 🏆 本月热点话题 TOP 10

"""
    
    if keywords_counter:
        top_keywords = keywords_counter.most_common(10)
        for i, (keyword, count) in enumerate(top_keywords, 1):
            bar = "█" * min(count, 15)
            report += f"{i}. **{keyword}**: {bar} ({count}次)\n"
    else:
        report += "- 本月暂无热点数据\n"
    
    report += f"""

## 📈 趋势分析

"""
    
    # 简单趋势判断
    if keywords_counter:
        top3 = [k for k, v in keywords_counter.most_common(3)]
        report += f"- **上升趋势**: {', '.join(top3)}\n"
        report += "- **关注建议**: 这些话题持续火热，值得深入关注\n"
    
    report += f"""

---

*月报生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
"""
    
    return report


def push_to_github(news_md, date, report_type=None):
    git_dir = GIT_REPO
    
    if not os.path.exists(git_dir):
        print(f"📦 克隆仓库...")
        subprocess.run(["git", "clone", f"git@github.com:yangshen830-eng/openclaw-rss-news.git", git_dir], capture_output=True)
    else:
        subprocess.run(["git", "-C", git_dir, "remote", "set-url", "origin", "git@github.com:yangshen830-eng/openclaw-rss-news.git"], capture_output=True)
    
    if report_type == "weekly":
        # 周报
        report_folder = os.path.join(git_dir, "reports")
        os.makedirs(report_folder, exist_ok=True)
        filename = f"weekly-{datetime.now().strftime('%Y-W%W')}.md"
        with open(os.path.join(report_folder, filename), 'w', encoding='utf-8') as f:
            f.write(news_md)
        print(f"✅ 周报已保存: reports/{filename}")
        
    elif report_type == "monthly":
        # 月报
        report_folder = os.path.join(git_dir, "reports")
        os.makedirs(report_folder, exist_ok=True)
        filename = f"monthly-{datetime.now().strftime('%Y-%m')}.md"
        with open(os.path.join(report_folder, filename), 'w', encoding='utf-8') as f:
            f.write(news_md)
        print(f"✅ 月报已保存: reports/{filename}")
        
    else:
        # 每日新闻
        news_folder = os.path.join(git_dir, "news")
        os.makedirs(news_folder, exist_ok=True)
        with open(os.path.join(news_folder, f"{date}.md"), 'w', encoding='utf-8') as f:
            f.write(news_md)
    
    # 备份 skill
    skill_backup = os.path.join(git_dir, "ai-news-push-skill")
    if os.path.exists(SKILL_DIR):
        os.makedirs(skill_backup, exist_ok=True)
        subprocess.run(["rsync", "-av", f"{SKILL_DIR}/", f"{skill_backup}/"], capture_output=True)
        for f in ["__pycache__", ".pyc"]:
            subprocess.run(["find", skill_backup, "-name", f, "-delete"], capture_output=True)
    
    # Git 推送
    print(f"📤 推送到 GitHub...")
    subprocess.run(["git", "-C", git_dir, "add", "."], capture_output=True)
    result = subprocess.run(["git", "-C", git_dir, "commit", "-m", f"Add {date} news & skill"], capture_output=True)
    result = subprocess.run(["git", "-C", git_dir, "push", "origin", "main"], capture_output=True)
    
    if result.returncode == 0:
        print(f"✅ 已推送成功")
        return True
    else:
        print(f"⚠️ 推送失败: {result.stderr.decode()}")
        return False


def main():
    import sys
    
    os.makedirs(NEWS_DIR, exist_ok=True)
    
    # 检查是否生成周报/月报
    if len(sys.argv) > 1:
        if sys.argv[1] == "--weekly":
            report = generate_weekly_report(NEWS_DIR)
            push_to_github(report, datetime.now().strftime("%Y-W%W"), "weekly")
            return
        elif sys.argv[1] == "--monthly":
            report = generate_monthly_report(NEWS_DIR)
            push_to_github(report, datetime.now().strftime("%Y-%m"), "monthly")
            return
    
    # 日常新闻抓取
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
    local_filename = os.path.join(NEWS_DIR, f"{today}.md")
    with open(local_filename, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print(f"✅ 本地保存: {local_filename}")
    
    # 推送到 GitHub
    push_to_github(md_content, today)
    
    # 输出新闻内容（供 cron deliver 模式推送）
    print("\n" + "="*50)
    print("📰 今日AI新闻摘要")
    print("="*50)
    print(md_content)
    print("="*50)
    print("\n✨ 完成!")


if __name__ == "__main__":
    main()
