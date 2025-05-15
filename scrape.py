import csv
import os
import time
import re
import sys
from playwright.sync_api import sync_playwright

'''def clean_text(text):
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = re.sub(' +', ' ', text)  # 移除多餘空格
    return text.strip()'''

def clean_text_safe(text):
    if not isinstance(text, str):
        text = str(text)
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ").replace('"', "'")
    text = re.sub(r"[\x00-\x1F\x7F]+", " ", text)  # 移除所有控制字元
    text = re.sub(r" +", " ", text)
    return text.strip()

def clean_row(row):
    return {
        "Title": clean_text_safe(row["Title"]),
        "Text": clean_text_safe(row["Text"]),
        "Category": clean_text_safe(row["Category"]),
        "URL": clean_text_safe(row["URL"])
    }

def extract_article_content(page):
    title = page.title().strip()
    texts = page.locator("div.article_body").all_inner_texts()
    full_text = "\n".join(texts).strip()
    return title, full_text

def run(output_filename):
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
                page.goto(url, timeout=60000)
                title, text = extract_article_content(page)
                category = article_category_map.get(url, "未知分類")

                results.append({
                    "Title": clean_text_safe(title),
                    "Text": clean_text_safe(text),
                    "Category": clean_text_safe(category),
                    "URL": url
                })
            except Exception as e:
                print(f"⚠️ 發生錯誤：{e}")
                continue

        browser.close()

        # 若有新資料，附加寫入
        if results:
            # 有新資料 → 重建整份 CSV 並整合舊資料
            dir_name = os.path.dirname(output_filename)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            existing_data = {}
            if os.path.exists(output_filename):
                with open(output_filename, "r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        existing_data[row["URL"]] = row

            # 更新或新增
            for row in results:
                existing_data[row["URL"]] = row

            with open(output_filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["Title", "Text", "Category", "URL"])
                writer.writeheader()
                for row in existing_data.values():
                    writer.writerow(row)

            print(f"\n✅ 新增或更新 {len(results)} 筆文章，已寫入 {output_filename}")

            # ✅ 回傳完整資料（已清理）
            return [clean_row(r) for r in existing_data.values()]

        else:
            # 沒新資料 → 寫一筆假資料
            dir_name = os.path.dirname(output_filename)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            with open(output_filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["Title", "Text", "Category", "URL"])
                writer.writeheader()
                writer.writerow({
                    "Title": 1,
                    "Text": 1,
                    "Category": 1,
                    "URL": 1
                })

            print("\n📭 沒有需要新增的文章，但已建立空檔案以供回傳。")

            return [{
                "Title": 1,
                "Text": 1,
                "Category": 1,
                "URL": 1
            }]
if __name__ == "__main__":
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "slack_articles_with_category.csv")
    run(output_file)
