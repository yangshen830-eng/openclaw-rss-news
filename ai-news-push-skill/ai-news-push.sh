#!/bin/bash
# AI News Push Script
# 每天抓取AI/科技新闻，整理成markdown

NEWS_DIR="${NEWS_DIR:-$HOME/ai-news}"
MAX_NEWS="${MAX_NEWS:-10}"
FEEDS="${FEEDS:-https://news.ycombinator.com/rss,https://openai.com/blog/rss.xml,https://36kr.com/newsflashes,https://www.technologyreview.com/feed/}"

TODAY=$(date +%Y-%m-%d)
OUTPUT_FILE="$NEWS_DIR/${TODAY}-news.md"

# Create directory if not exists
mkdir -p "$NEWS_DIR"

echo "# AI&科技每日新闻 - $TODAY" > "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Parse feeds (simplified - extracts titles and links)
count=0

IFS=',' read -ra FEED_ARRAY <<< "$FEEDS"
for feed in "${FEED_ARRAY[@]}"; do
    echo "📡 正在抓取: $feed"
    
    # Get feed content
    content=$(curl -s --max-time 30 "$feed" 2>/dev/null)
    
    if [ -n "$content" ]; then
        # Extract titles (simplified parsing - works with RSS/Atom)
        titles=$(echo "$content" | grep -oP '<title><!\[CDATA\[(.*?)\]\]></title>|<title>(.*?)</title>' | sed 's/<title>//g;s/<\/title>//g;s/<!\[CDATA\[//g;s/\]\]>//g' | tail -n +2)
        
        # Also get links
        links=$(echo "$content" | grep -oP '<link>(.*?)</link>' | sed 's/<link>//g;s/<\/link>//g' | head -n 5)
        
        # Extract description/summary
        descriptions=$(echo "$content" | grep -oP '<description><!\[CDATA\[(.*?)\]\]></description>|<description>(.*?)</description>' | sed 's/<description>//g;s/<\/description>//g;s/<!\[CDATA\[//g;s/\]\]>//g' | head -n 5)
    fi
    
    count=$((count + 1))
done

echo "" >> "$OUTPUT_FILE"
echo "> 数据来源: Hacker News, OpenAI Blog, 36kr, MIT Tech Review" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

echo "✅ 新闻已保存至: $OUTPUT_FILE"
echo "📰 共抓取 RSS 源: ${#FEED_ARRAY[@]}"
