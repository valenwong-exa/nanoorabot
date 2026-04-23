# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('oracle_ai_blogs_20260421.txt', 'r', encoding='utf-8') as f:
    content = f.read()

# Split by article separator (assuming each article starts with "标题:")
articles = content.split('\n标题:')

print(f"Total articles found: {len(articles)}")
print("=" * 80)

for i, article in enumerate(articles):
    if not article.strip():
        continue
    
    # Extract title
    lines = article.split('\n')
    title = lines[0].strip() if lines else "Unknown"
    
    # Extract URL
    url = ""
    for line in lines:
        if line.startswith('URL:'):
            url = line.replace('URL:', '').strip()
            break
    
    # Extract first 500 chars of content for summary
    content_start = article.find('内容:')
    if content_start > 0:
        content_text = article[content_start:content_start+800]
    else:
        content_text = article[:800]
    
    print(f"\n--- Article {i} ---")
    print(f"Title: {title}")
    print(f"URL: {url}")
    print(f"Preview: {content_text[:500]}...")
    print("-" * 80)
