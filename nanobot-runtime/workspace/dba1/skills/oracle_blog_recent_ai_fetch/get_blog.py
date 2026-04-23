import argparse
from pathlib import Path

SEPARATOR = "\n" + ("-" * 80) + "\n"
NO_ARTICLE_TEXT = "最近30天内没有匹配关键词且符合日期条件的文章。"


def split_articles(text: str) -> list[str]:
    text = text.strip()
    if not text or text == NO_ARTICLE_TEXT:
        return []

    parts = [part.strip() for part in text.split(SEPARATOR)]
    articles = [part for part in parts if part and part != NO_ARTICLE_TEXT]
    return articles


def main():
    parser = argparse.ArgumentParser(
        description="Count blog articles in an output txt file, or extract one article by 1-based index."
    )
    parser.add_argument("txt_file", help="Blog output txt file path, for example oracle_ai_blogs_20260420.txt")
    parser.add_argument(
        "article_no",
        nargs="?",
        type=int,
        help="1-based article number to extract. Omit it to print total article count.",
    )
    args = parser.parse_args()

    file_path = Path(args.txt_file)
    if not file_path.exists():
        raise SystemExit(f"File not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")
    articles = split_articles(content)

    if args.article_no is None:
        print(f"article_count={len(articles)}")
        return

    if args.article_no < 1:
        raise SystemExit("article_no must be >= 1")

    if not articles:
        raise SystemExit("No articles found in the txt file.")

    if args.article_no > len(articles):
        raise SystemExit(f"article_no out of range: {args.article_no}, total={len(articles)}")

    print(articles[args.article_no - 1])


if __name__ == "__main__":
    main()
