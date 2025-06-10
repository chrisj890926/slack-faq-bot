import os
import re
import time
import json
from datetime import datetime
from playwright.sync_api import sync_playwright

def clean_text(text):
    text = text.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    text = re.sub(' +', ' ', text)
    return text.strip()

def extract_article_content(page):
    title = page.title().strip()
    texts = page.locator("div.article_body").all_inner_texts()
    full_text = "\n".join(texts).strip()
    return title, full_text

def run(output_filename):
    print("📂 將從零開始爬資料，覆蓋舊檔案")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        BASE_URL = "https://slack.com/intl/zh-tw/help"
        page.goto(BASE_URL)

        category_links = list(set(
            page.locator("a[href*='/help/categories/']").evaluate_all(
                "links => Array.from(links, a => a.href)"
            )
        ))
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
            print(f"🔍 正在處理第 {idx+1}/{len(article_urls)} 篇: {url}")
            try:
                page.goto(url, timeout=60000)
                title, text = extract_article_content(page)
                category = article_category_map.get(url, "未知分類")
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

        dir_name = os.path.dirname(output_filename)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

        with open(output_filename, "w", encoding="utf-8-sig") as f:
            f.write("Title$Text$Category$URL\n")
            if results:
                for row in results:
                    def clean(val): return str(val).replace("$", "＄")
                    line = f"{clean(row['Title'])}${clean(row['Text'])}${clean(row['Category'])}${row['URL']}\n"
                    f.write(line)
                print(f"✅ 寫入 {len(results)} 筆資料")
            else:
                f.write(f"空資料$空資料$空資料$empty-{datetime.now().isoformat()}\n")
                print("📭 無新資料，已建立空檔案")

if __name__ == "__main__":
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "slack_articles_with_category.txt")
    run(output_file)
