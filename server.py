from flask import Flask, request, send_file, jsonify
import subprocess
import os

app = Flask(__name__)

@app.route("/trigger-scrape", methods=["POST"])
def trigger_scrape():
    try:
        print("✅ 收到 POST 請求，開始執行爬蟲...")

        # 設定與 scrape.py 相同的輸出路徑
        output_path = os.path.join("output", "slack_articles_with_category.csv")
        os.makedirs("output", exist_ok=True)  # 確保 output 資料夾存在

        # 執行 scrape.py
        process = subprocess.Popen(["python", "scrape.py"])
        process.wait()

        print("✅ 爬蟲執行完畢，準備傳回 CSV")

        # 確保檔案存在後再傳送
        if not os.path.exists(output_path):
            return jsonify({"status": "error", "message": "CSV 檔案未產生"}), 500

        return send_file(
            output_path,
            mimetype="text/csv",
            as_attachment=True,
            download_name="slack_articles_with_category.csv"
        )

    except Exception as e:
        print("❌ 發生例外錯誤：", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/", methods=["GET"])
def health():
    return "✅ Slack FAQ Bot is running!"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
