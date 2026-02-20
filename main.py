# main.py
from flask import Flask, request, jsonify
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import os
import requests

app = Flask(__name__)

# 环境变量里配置
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
MY_AMZ_TAG = os.getenv("MY_AMZ_TAG", "yiyigao0e-22")  # 你的联盟 tag

def send_discord(message: str):
    if not DISCORD_WEBHOOK_URL:
        print("未设置 DISCORD_WEBHOOK_URL")
        return
    try:
        resp = requests.post(
            DISCORD_WEBHOOK_URL,
            json={"content": message},
            timeout=10,
        )
        print("Discord 推送:", resp.status_code, resp.text)
    except Exception as e:
        print("发送 Discord 失败:", e)

def replace_amazon_tag(url: str) -> str:
    if "amazon." not in url:
        return url
    parsed = urlparse(url)

    # 去掉 Amazon 的短链参数等，只保留必要的 + 你的 tag
    qs = parse_qs(parsed.query)
    qs["tag"] = [MY_AMZ_TAG]

    new_qs = urlencode(qs, doseq=True)
    new_parsed = parsed._replace(query=new_qs)
    new_url = urlunparse(new_parsed)
    print("重写 Amazon 链接:", url, "->", new_url)
    return new_url

def extract_urls_from_text(text: str):
    # 简单版本：按空格/换行分隔的 URL
    urls = re.findall(r"https?://\S+", text)
    return urls

def build_affiliate_links(urls):
    new_urls = []
    for u in urls:
        if "amazon." in u:
            new_urls.append(replace_amazon_tag(u))
        else:
            # 其它平台先原样保留，之后你可以按平台扩展
            new_urls.append(u)
    return new_urls

@app.route("/webhook", methods=["POST"])
def handle_tweet():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"status": "no_json"}), 400

    # 第三方通常会给你 tweet 文本和一个唯一 ID
    text = data.get("text") or ""
    tweet_id = data.get("id") or data.get("tweet_id")  # 兼容不同服务字段
    username = data.get("username") or data.get("user", {}).get("screen_name")

    print("收到推文:", tweet_id, "from", username)
    print("原文:", text)

    urls = extract_urls_from_text(text)
    if not urls:
        print("没有检测到 URL，跳过发送。")
        return jsonify({"status": "no_urls"}), 200

    aff_urls = build_affiliate_links(urls)

    # 只发你自己的整理，不写来源
    # 你可以按喜好调整格式
    msg_lines = []
    msg_lines.append("📢 新情报（自动整理）")
    msg_lines.append("")
    msg_lines.append("链接：")
    for i, u in enumerate(aff_urls, 1):
        msg_lines.append(f"{i}. {u}")

    message = "\n".join(msg_lines)
    send_discord(message)

    return jsonify({"status": "ok"}), 200

@app.route("/", methods=["GET"])
def health():
    return "OK", 200

if __name__ == "__main__":
    # 本地调试用，Cloud Run/Render 会用 gunicorn 启动
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
