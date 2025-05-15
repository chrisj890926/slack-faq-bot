import csv
import os
import time
import re
import sys
from playwright.sync_api import sync_playwright

def clean_text_safe(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ").replace('"', "'")
    text = re.sub(r"[\x00-\x1F\x7F]+", " ", text)
    text = re.sub(r" +", " ", text)
    return text.strip()

def extract_article_content(page):
    title = page.title().strip()
    texts = page.locator("div.article_body").all_inner_texts()
    full_text = "\n".join(texts).strip()
    return title, full_text

def run(output_filename):
    existing_data = {}
    if os.path.exists(output_filename):
        with open(output_filename, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_data[row["URL"]] = row
        print(f"🧠 已讀取 {len(existing_data)} 筆舊資料")
    else:
        print("🆕 沒有既有 CSV，將從零開始爬")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        BASE_URL = "https://slack.com/intl/zh-tw/help"
        page.goto(BASE_URL)

        category_links = page.locator("a[href*='/help/categories/']").evaluate_all(
            "links => Array.from(links, a => a.href)"
        )
        category_links = list(set(category_links))
        print(f"✅ 發現 {len(category_links)} 個分類")

        article_urls = []
        article_category_map = {}

        for cat_url in category_links:
            page.goto(cat_url)
            links = page.locator("a[href*='/help/articles/']").evaluate_all(
                "links => Array.from(links, a => a.href)"
            )
            for link in links:
                article_urls.append(link)
                article_category_map[link] = cat_url
            time.sleep(1)

        article_urls = list(set(article_urls))
        print(f"📝 共發現 {len(article_urls)} 篇文章")

        has_update = False

        for idx, url in enumerate(article_urls):
            print(f"🔍 第 {idx+1}/{len(article_urls)} 篇: {url}")
            try:
                page.goto(url, timeout=60000)
                title, text = extract_article_content(page)
                category = article_category_map.get(url, "未知分類")

                new_row = {
                    "Title": clean_text_safe(title),
                    "Text": clean_text_safe(text),
                    "Category": clean_text_safe(category),
                    "URL": clean_text_safe(url)
                }

                old_row = existing_data.get(url)
                if old_row is None or any(old_row[k] != new_row[k] for k in ["Title", "Text", "Category"]):
                    existing_data[url] = new_row
                    has_update = True
            except Exception as e:
                print(f"⚠️ 發生錯誤：{e}")
                continue

        browser.close()

    # 寫入整份資料
    dir_name = os.path.dirname(output_filename)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    with open(output_filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["Title", "Text", "Category", "URL"])
        writer.writeheader()
        for row in existing_data.values():
            writer.writerow(row)

    if has_update:
        print(f"\n✅ 有更新，已寫入 {len(existing_data)} 筆資料")
        return list(existing_data.values())
    else:
        print("\n📭 沒有任何更新，回傳假資料")
        return [{"Title": 1, "Text": 1, "Category": 1, "URL": 1}]

if __name__ == "__main__":
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "slack_articles_with_category.csv")
    result = run(output_file)
    print(f"📦 共回傳 {len(result)} 筆資料")