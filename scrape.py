import csv
import os
import time
import re
import sys
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
                # 測試用
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

        # 若有新資料，附加寫入
        if results:
            # 將 results 轉為 JSON 格式
            json_data = json.dumps(results, ensure_ascii=False, indent=2)
            print(json_data)  # 你也可以先印出來看看結果

            dir_name = os.path.dirname(output_filename)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            file_exists = os.path.exists(output_filename)
            with open(output_filename, "a", newline="", encoding="utf-8-sig") as f: 
                writer = csv.DictWriter(f, fieldnames=["Title", "Text", "Category", "URL"])
                if not file_exists or not existing_urls:
                    writer.writeheader()
                for row in results:
                    writer.writerow(row)

            print(f"\n✅ 新增 {len(results)} 筆文章，已寫入 {output_filename}")
        '''
        else:
            # 即使沒新資料也要建立空檔
            '''
            # 產生新的檔案名稱
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            empty_filename = os.path.join(output_dir, f"empty_{timestamp}.csv")

            # 建立資料夾（如果不存在）
            dir_name = os.path.dirname(empty_filename)
            if dir_name:
                os.makedirs(dir_name, exist_ok=True)

            # 寫入「空資料檔案」，不會覆蓋原本檔案
            with open(empty_filename, "w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=["Title", "Text", "Category", "URL"])
                writer.writeheader()
                writer.writerow({
                    "Title": 1,
                    "Text": 1,
                    "Category": 1,
                    "URL": f"empty-{datetime.now().isoformat()}"
                })
            '''
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
                    "URL": f"empty-{datetime.now().isoformat()}"
                })

            
            print("\n📭 沒有需要新增的文章，但已建立空檔案以供回傳。")
        '''
if __name__ == "__main__":
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, "slack_articles_with_category.csv")
   

    run(output_file)
