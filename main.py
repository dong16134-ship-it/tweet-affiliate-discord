from playwright.sync_api import sync_playwright
import requests
import time
import os

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
AMAZON_TAG = os.getenv("AMAZON_TAG", "yiyigao0e-22")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "60"))  # 每隔多少秒检查一次

PRODUCTS = [
    {
        "name": "Apple iPhone 15 Pro Max 256GB コズミックオレンジ",
        "url": "https://www.amazon.co.jp/dp/B0FQGJTF74",
        "asin": "B0FQGJTF74",
    },
]

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

def check_amazon_in_stock(page, url: str) -> bool | None:
    # 打开页面
    page.goto(url, wait_until="domcontentloaded", timeout=60000)

    # 取整页文本
    body_text = page.text_content("body") or ""

    # 典型有货/无货文案（可以后面根据实际页面再微调）
    in_words = [
        "カートに入れる",
        "今すぐ購入",
        "お客様のお届け先にお届け",
    ]
    out_words = [
        "現在お取り扱いできません",
        "一時的に在庫切れ",
        "在庫切れです",
        "この商品は現在お取り扱いできません",
    ]

    if any(w in body_text for w in out_words):
        return False
    if any(w in body_text for w in in_words):
        return True
    return None  # 看不出来

def run_loop():
    last_status = {}  # url -> bool

    with sync_playwright() as p:
        while True:
            try:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                print("开始一轮检查...")

                for item in PRODUCTS:
                    name = item["name"]
                    url = item["url"]
                    asin = item["asin"]

                    print(f"检查 {name}: {url}")
                    status = check_amazon_in_stock(page, url)
                    print("有货判定:", status)

                    prev = last_status.get(url)

                    # 从“无货/未知” -> “有货” 时才通知
                    if status and prev is not True:
                        aff_link = f"https://www.amazon.co.jp/dp/{asin}?tag={AMAZON_TAG}"
                        msg = (
                            f"✅ Amazon 有货：{name}\n"
                            f"🔗 {aff_link}"
                        )
                        send_discord(msg)
                        last_status[url] = True
                    elif status is False:
                        last_status[url] = False

                browser.close()
            except Exception as e:
                print("本轮检查异常:", e)

            print(f"休眠 {CHECK_INTERVAL} 秒\n")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    run_loop()
