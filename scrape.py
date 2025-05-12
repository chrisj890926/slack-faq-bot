import csv
import os
import time
import sys
from playwright.sync_api import sync_playwright

def extract_article_content(page):
    title = page.title().strip()
    texts = page.locator("div.article_body").all_inner_texts()
    full_text = "\n".join(texts).strip()
    return title, full_text

def run(output_filename):
    # 建立已存在的 URL set（避免重複抓）
    existing_urls = set()
    if os.path.exists(output_filename):
        with open(output_filename, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_urls.add(row["URL"])
        print(f"🧠 已爬過 {len(existing_urls)} 篇文章，將跳過這些 URL")
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

        results = []

        for idx, url in enumerate(article_urls):
            if url in existing_urls:
                print(f"⏩ 跳過已爬過文章 ({idx+1}/{len(article_urls)}): {url}")
                continue

            print(f"🔍 正在處理第 {idx+1}/{len(article_urls)} 篇: {url}")
            try:
                page.goto(url)
                title, text = extract_article_content(page)
                category = article_category_map.get(url, "未知分類")
                results.append({
                    "Title": title,
                    "Text": text,
                    "Category": category,
                    "URL": url
                })
            except Exception as e:
                print(f"⚠️ 發生錯誤：{e}")
                continue

        browser.close()

        # 若有新資料，附加寫入 CSV
        if results:
            os.makedirs(os.path.dirname(output_filename), exist_ok=True)
            file_exists = os.path.exists(output_filename)
            with open(output_filename, "a", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["Title", "Text", "Category", "URL"])
                if not file_exists or not existing_urls:
                    writer.writeheader()
                for row in results:
                    writer.writerow(row)

            print(f"\n✅ 新增 {len(results)} 筆文章，已寫入 {output_filename}")
        else:
            # 📭 沒有新資料，但仍確保檔案存在（為 Flask 傳檔）
            if not os.path.exists(output_filename):
                os.makedirs(os.path.dirname(output_filename), exist_ok=True)
                with open(output_filename, "w", newline="", encoding="utf-8-sig") as f:
                    writer = csv.DictWriter(f, fieldnames=["Title", "Text", "Category", "URL"])
                    writer.writeheader()
            print("\n📭 沒有需要新增的文章，但已建立空檔案以供回傳。")


# 執行點
if __name__ == "__main__":
    output_file = "slack_articles_with_category.csv"
    run(output_file)
