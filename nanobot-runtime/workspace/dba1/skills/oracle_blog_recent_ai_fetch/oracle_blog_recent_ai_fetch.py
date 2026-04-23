import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BASE_URL = "https://blogs.oracle.com/"
SCOPED_BLOG_BASE_URLS = [
    "https://blogs.oracle.com/analytics/",
    "https://blogs.oracle.com/ai-and-datascience/",
    "https://blogs.oracle.com/database/",
    "https://blogs.oracle.com/developers/",
    "https://blogs.oracle.com/cloud-infrastructure/",
    "https://blogs.oracle.com/apex/",
]
KEYWORD_PATTERN = re.compile(r"\bAI\b|AI AGENT|VECTOR|MCP|GPU|NVIDA|APEX|ONNX|AGENT|EMBEDDING|GENERATIVE AI|CODE ASSISTANT|AI ASSISTANT|LLM|REACT|AGENT LOOP|SELECT AI|ROBOT|AI-POWERED|AGENTIC|AUTONOMOUS|26AI|CLAW|OPENAI|CLAUDE|GEMINI|NL2SQL|NLQ|CLOUD_AI|QWEN|DEEPSEEK|GLM|KIMI|MINMAX|GORK", re.IGNORECASE)
MAX_ARTICLE_CANDIDATES = 120


def title_matches(title: str) -> bool:
    if not title:
        return False
    return bool(KEYWORD_PATTERN.search(title))


def goto_with_retry(page, url, timeout=45000, retries=2):
    last_error = None
    for _ in range(retries + 1):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            return
        except Exception as e:
            last_error = e
            page.wait_for_timeout(1500)
    raise last_error


def parse_datetime(value: str):
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def extract_sitemap_urls(page):
    # Restrict scan scope to user-specified Oracle blog sections only.
    return [f"{base.rstrip('/')}/wp-sitemap.xml" for base in SCOPED_BLOG_BASE_URLS]


def extract_article_candidates(page, sitemap_urls, threshold):
    candidates = []
    seen = set()

    for idx, sitemap_url in enumerate(sitemap_urls, 1):
        try:
            print(f"Scanning sitemap {idx}/{len(sitemap_urls)}: {sitemap_url}")
            goto_with_retry(page, sitemap_url)
            body_text = page.inner_text("body")
            child_sitemaps = []
            for line in body_text.splitlines():
                line = line.strip()
                if not line.startswith("https://blogs.oracle.com/"):
                    continue
                child_url = line.split()[0].strip()
                if "wp-sitemap-posts-post-" not in child_url:
                    continue
                child_sitemaps.append(child_url)

            for child_url in child_sitemaps:
                goto_with_retry(page, child_url)
                child_text = page.inner_text("body")
                for line in child_text.splitlines():
                    line = line.strip()
                    if not line.startswith("https://blogs.oracle.com/"):
                        continue
                    parts = line.split()
                    link = parts[0].strip()
                    if "wp-sitemap" in link:
                        continue
                    if link in seen:
                        continue
                    seen.add(link)

                    parsed = urlparse(link)
                    if "blogs.oracle.com" not in parsed.netloc.lower():
                        continue
                    if not parsed.path or parsed.path == "/":
                        continue
                    if not any(link.startswith(base) for base in SCOPED_BLOG_BASE_URLS):
                        continue

                    date_text = parts[-1].strip() if len(parts) >= 2 else ""
                    lastmod_dt = parse_datetime(date_text)

                    if lastmod_dt and lastmod_dt < threshold:
                        continue

                    candidates.append((link, lastmod_dt))
                    if len(candidates) >= MAX_ARTICLE_CANDIDATES:
                        return candidates
        except Exception as e:
            print(f"Skip sitemap due to error: {e}")

    return candidates


def get_article_title(page):
    h1 = page.query_selector("h1")
    if h1:
        text = (h1.inner_text() or "").strip()
        if text:
            return text
    return (page.title() or "").strip()


def extract_article_datetime(page):
    meta_date = page.evaluate(
        """() => {
            const selectors = [
                'meta[property="article:published_time"]',
                'meta[name="article:published_time"]',
                'meta[property="og:published_time"]',
                'meta[name="publish_date"]',
                'meta[name="date"]'
            ];
            for (const sel of selectors) {
                const node = document.querySelector(sel);
                if (node) {
                    const v = node.getAttribute('content') || node.getAttribute('value');
                    if (v) return v;
                }
            }
            const timeNode = document.querySelector('time[datetime]');
            if (timeNode) {
                const v = timeNode.getAttribute('datetime');
                if (v) return v;
            }
            return '';
        }"""
    )

    dt = parse_datetime(meta_date)
    if dt:
        return dt

    blocks = page.query_selector_all('script[type="application/ld+json"]')
    for block in blocks:
        raw = block.inner_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("datePublished", "dateCreated", "dateModified"):
                dt = parse_datetime(str(item.get(key, "")))
                if dt:
                    return dt
    return None


def extract_page_content(page):
    page.evaluate(
        """() => {
            const selectorsToRemove = [
                'nav', 'footer', '.footer', '.sidebar', '.nav', '.navigation',
                '.menu', '#menu', '.ad', '.ads', '.advertisement',
                'script', 'style', 'noscript', 'iframe'
            ];
            selectorsToRemove.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => el.remove());
            });
        }"""
    )

    for selector in ["main", "article", ".content", "#content", "body"]:
        el = page.query_selector(selector)
        if not el:
            continue
        text = (el.inner_text() or "").strip()
        if not text:
            continue
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        return "\n".join(lines)
    return ""


def browser_candidate_names():
    if sys.platform.startswith("win"):
        return ["chrome.exe", "msedge.exe", "chromium.exe"]
    if sys.platform == "darwin":
        return [
            "Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
            "Google Chrome.app/Contents/MacOS/Google Chrome",
            "Chromium.app/Contents/MacOS/Chromium",
            "Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    return ["chrome", "google-chrome", "chromium", "chromium-browser", "msedge"]


def first_existing_path(paths):
    for path in paths:
        if os.path.isfile(path):
            return path
    return None


def resolve_chrome_path(current_dir: str):
    candidates = []
    names = browser_candidate_names()

    chrome_home = os.environ.get("CHROME_HOME", "").strip()
    if chrome_home:
        if os.path.isfile(chrome_home):
            candidates.append(("CHROME_HOME", chrome_home))
        else:
            path = first_existing_path([os.path.join(chrome_home, name) for name in names])
            if path:
                candidates.append(("CHROME_HOME", path))

    path = first_existing_path([os.path.join(current_dir, name) for name in names])
    if path:
        candidates.append(("current_dir", path))

    workspace_root = os.path.dirname(os.path.dirname(current_dir))
    path = first_existing_path([os.path.join(workspace_root, name) for name in names])
    if path:
        candidates.append(("workspace_root", path))

    for source, path in candidates:
        return source, path
    return None, None


def fetch_recent_articles(days=30):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    chrome_source, chrome_path = resolve_chrome_path(current_dir)

    threshold = datetime.now(timezone.utc) - timedelta(days=days)
    output_filename = f"oracle_ai_blogs_{datetime.now().strftime('%Y%m%d')}.txt"
    output_path = os.path.join(current_dir, output_filename)
    read_history_path = os.path.join(current_dir, "has_been_read.txt")
    output_blocks = []
    read_urls = set()
    newly_read_urls = []
    time_matched_count = 0

    if os.path.exists(read_history_path):
        with open(read_history_path, "r", encoding="utf-8") as f:
            read_urls = {line.strip() for line in f if line.strip()}

    with sync_playwright() as p:
        launch_kwargs = {
            "headless": False,
            "args": ["--no-sandbox", "--disable-infobars"],
        }
        if chrome_path:
            print(f"Using Chrome from {chrome_source}: {chrome_path}")
            launch_kwargs["executable_path"] = chrome_path
        else:
            names = browser_candidate_names()
            print("Chrome not found in CHROME_HOME, current skill directory, or workspace root.")
            print(f"Tried browser names for this platform: {', '.join(names)}")
            print("Falling back to Playwright Chromium.")
            print("If browser launch fails, run: playwright install chromium")

        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context()
        page = context.new_page()

        print(f"Opening: {BASE_URL}")
        goto_with_retry(page, BASE_URL)
        page.wait_for_timeout(2000)

        sitemap_urls = extract_sitemap_urls(page)
        print(f"Sitemaps selected: {len(sitemap_urls)}")

        candidates = extract_article_candidates(page, sitemap_urls, threshold)
        print(f"Article candidates: {len(candidates)}")

        found_recent = 0
        for idx, (url, sitemap_lastmod) in enumerate(candidates, 1):
            if sitemap_lastmod and sitemap_lastmod < threshold:
                continue
            if url in read_urls:
                print(f"[{idx}] Skip already-read URL: {url}")
                continue

            article_page = context.new_page()
            try:
                goto_with_retry(article_page, url)
                title = get_article_title(article_page)
                if not title_matches(title):
                    continue

                published_dt = extract_article_datetime(article_page) or sitemap_lastmod
                if not published_dt:
                    print(f"[{idx}] Skip date-not-found: {title}")
                    continue

                if published_dt < threshold:
                    print(f"[{idx}] Skip old article: {title} ({published_dt.isoformat()})")
                    continue

                time_matched_count += 1
                content = extract_page_content(article_page)
                if not content:
                    print(f"[{idx}] Skip empty-content: {title}")
                    continue

                found_recent += 1
                print("\n" + "=" * 100)
                print(f"[{found_recent}] {title}")
                print(f"URL: {url}")
                print(f"Published (UTC): {published_dt.isoformat()}")
                print("-" * 100)
                print(content)
                print("=" * 100)
                output_blocks.append(
                    "\n".join(
                        [
                            f"标题: {title}",
                            f"URL: {url}",
                            "内容:",
                            content,
                        ]
                    )
                )
                newly_read_urls.append(url)
            except Exception as e:
                print(f"[{idx}] Error processing {url}: {e}")
            finally:
                article_page.close()

        if found_recent == 0:
            print(f"\nNo matching articles in the last {days} days.")
            output_blocks.append("45")

        separator = "\n" + ("-" * 80) + "\n"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(separator.join(output_blocks))
        print(f"\nSaved result file: {output_path}")
        print(f"发现 {time_matched_count} 篇满足时间要求的文章。")

        if newly_read_urls:
            with open(read_history_path, "a", encoding="utf-8") as f:
                for item_url in newly_read_urls:
                    f.write(item_url + "\n")
            print(f"已更新已读URL文件: {read_history_path} (新增 {len(newly_read_urls)} 条)")
        else:
            print(f"已读URL文件未新增记录: {read_history_path}")

        browser.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch recent Oracle AI blogs.")
    parser.add_argument("--days", type=int, default=30, help="Number of days to look back for recent articles (default: 30)")
    args = parser.parse_args()
    
    fetch_recent_articles(days=args.days)
