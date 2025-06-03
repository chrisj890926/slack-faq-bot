import csv
import os
import time
import re
import sys
import shutil

import json
from playwright.sync_api import sync_playwright
from datetime import datetime


def clean_text(text):
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = re.sub(' +', ' ', text)  # 移除多餘空格
    return text.strip()

def extract_article_content(page):
    title = page.title().strip()
    texts = page.locator("div.article_body").all_inner_texts()
    full_text = "\n".join(texts).strip()
    return title, full_text
def files_are_equal(file1, file2):
    if not os.path.exists(file2):
        return False
    with open(file1, "r", encoding="utf-8-sig") as f1, open(file2, "r", encoding="utf-8-sig") as f2:
        return f1.read() == f2.read()

def run(output_file, previous_file):
    existing_urls = set()
    if os.path.exists(previous_file):
        with open(previous_file, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_urls.add(row["URL"])
        print(f"🧠 已爬過 {len(existing_urls)} 篇文章，將跳過這些 URL")
    else:
        print("🆕 沒有 previous_file，將從零開始爬")

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
                if idx == 0:
                    title += " 測試改1"

                results.append({
                    "Title": clean_text(title),
                    "Text": clean_text(text),
                    "Category": clean_text(category),
                    "URL": url
                })
            except Exception as e:
                print(f"⚠️ 發生錯誤：{e}")
                continue

        browser.close()

        # 寫入 output_file（本次新結果）
        with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=["Title", "Text", "Category", "URL"])
            writer.writeheader()
            if results:
                for row in results:
                    writer.writerow(row)
            else:
                # 沒新資料也先照原樣寫入空檔（之後再覆蓋為 dummy）
                pass

        # 檢查是否與 previous_file 相同
        if files_are_equal(output_file, previous_file):
            print("📭 資料相同，不更新 previous_file，覆蓋 output_file 為 dummy")
            with open(output_file, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["Title", "Text", "Category", "URL"])
                writer.writeheader()
                writer.writerow({
                    "Title": 1,
                    "Text": 1,
                    "Category": 1,
                    "URL": f"empty-{datetime.now().isoformat()}"
                })
            return output_file
        else:
            print("✅ 資料有更新，已寫入 previous_file")
            shutil.copy(output_file, previous_file)
            return output_file
if __name__ == "__main__":
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    output_file = os.path.join(output_dir, "slack_articles_with_category.csv")   # 新爬的
    previous_file = os.path.join(output_dir, "slack_articles_previous.csv")      # 上一次的

    result_path = run(output_file, previous_file)
