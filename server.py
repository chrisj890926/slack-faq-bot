from flask import Flask, request, send_file, jsonify
import subprocess
import datetime
import os

app = Flask(__name__)

@app.route("/trigger-scrape", methods=["POST"])
def trigger_scrape():
    try:
        print("✅ 收到 POST 請求，開始執行爬蟲...")

        # 輸出檔名固定為這份 CSV
        output_path = "slack_articles_with_category.csv"
        os.makedirs("output", exist_ok=True)

        # 執行爬蟲（使用 Popen 讓爬蟲 log 實時顯示在 Flask 終端）
        process = subprocess.Popen(["python", "scrape.py", output_path])
        process.wait()

        print("✅ 爬蟲執行完畢，準備傳回 CSV")
        return send_file(
            output_path,
            mimetype="text/csv",
            as_attachment=True,
            download_name="slack_articles_with_category.csv"
        )

    except Exception as e:
        print("❌ 發生例外錯誤：", str(e))
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
