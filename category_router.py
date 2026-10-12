"""
按商品类别把消息分流到不同的 Discord 频道（方案一）。

用法（在原来发 Discord 的地方替换）：
    from category_router import route_and_send
    route_and_send(text, extra_payload)   # text = 推文正文 / 商品标题

每个频道一个 Webhook，用环境变量配置：
    WEBHOOK_ALL      全合集（每条都发）
    WEBHOOK_GAME     🎮 游戏机
    WEBHOOK_CARD     🃏 卡牌
    WEBHOOK_FIGURE   🧸 手办潮玩
    WEBHOOK_DIGITAL  📱 数码家电
    WEBHOOK_DAILY    🍶 酒类食品日用
    WEBHOOK_OTHER    📦 其他（没命中任何类别时）
没配的类别会自动落到“其他”。
"""
import os
import re
import requests

# 顺序就是优先级：先命中的类别生效。
# 卡牌放在手办前面，避免 “ポケモンカード” 被 “ポケモン” 分进手办。
CATEGORIES = [
    ("CARD", "🃏 卡牌", [
        "ポケモンカード", "ポケカ", "遊戯王", "ワンピースカード", "ONE PIECEカード",
        "デュエマ", "デュエル・マスターズ", "ヴァイスシュヴァルツ", "ユニオンアリーナ",
        "ドラゴンボールスーパーカード", "MTG", "マジック:ザ・ギャザリング",
        "拡張パック", "強化拡張", "ハイクラスパック", "スターターデッキ", "BOX", "ボックス",
        "宝可梦卡", "卡牌", "卡包",
    ]),
    ("GAME", "🎮 游戏机", [
        "PS5", "PS4", "PlayStation", "プレイステーション", "プレステ", "DualSense",
        "Nintendo Switch", "ニンテンドースイッチ", "Switch 2", "Switch2", "スイッチ",
        "Xbox", "Steam Deck", "ROG Ally", "Joy-Con", "プロコン", "amiibo",
        "游戏机", "主机", "乐天ps",
    ]),
    ("FIGURE", "🧸 手办潮玩", [
        "フィギュア", "ねんどろいど", "figma", "一番くじ", "プライズ", "ガンプラ",
        "プラモデル", "HG ", "MG ", "RG ", "PG ", "ぬいぐるみ", "トミカ", "レゴ", "LEGO",
        "ちいかわ", "POP MART", "ポップマート", "LABUBU", "ラブブ", "超合金",
        "手办", "潮玩", "盲盒",
    ]),
    ("DIGITAL", "📱 数码家电", [
        "iPhone", "iPad", "Mac", "AirPods", "Apple Watch", "Pixel", "Galaxy",
        "カメラ", "レンズ", "ミラーレス", "Sony", "ソニー", "Canon", "キヤノン",
        "Nikon", "ニコン", "FUJIFILM", "富士フイルム", "instax", "チェキ", "GoPro", "DJI",
        "イヤホン", "ヘッドホン", "SSD", "グラボ", "RTX", "ドライヤー", "ダイソン", "Dyson",
        "掃除機", "炊飯器", "家電", "数码", "相机", "耳机",
    ]),
    ("DAILY", "🍶 酒类食品日用", [
        "ウイスキー", "山崎", "白州", "響", "竹鶴", "余市", "宮城峡", "イチローズモルト",
        "日本酒", "獺祭", "十四代", "焼酎", "ビール", "ワイン", "シャンパン",
        "お菓子", "食品", "飲料", "洗剤", "日用品", "化粧品", "コスメ", "サプリ",
        "威士忌", "酒", "零食", "日用",
    ]),
]

PLATFORMS = [
    ("亚马逊", ["amazon.co.jp", "amzn.to", "amzn.asia", "Amazon", "アマゾン"]),
    ("乐天", ["rakuten.co.jp", "a.r10.to", "楽天", "Rakuten"]),
    ("雅虎", ["shopping.yahoo.co.jp", "yahoo.co.jp", "PayPay", "Yahoo"]),
]

ENV_KEY = {
    "CARD": "WEBHOOK_CARD",
    "GAME": "WEBHOOK_GAME",
    "FIGURE": "WEBHOOK_FIGURE",
    "DIGITAL": "WEBHOOK_DIGITAL",
    "DAILY": "WEBHOOK_DAILY",
    "OTHER": "WEBHOOK_OTHER",
}


def _contains(text: str, word: str) -> bool:
    # 纯英文/数字关键词按单词边界匹配，避免 "Mac" 命中 "Machine"、"BOX" 命中 "Xbox"
    if re.fullmatch(r"[A-Za-z0-9 \-]+", word):
        pattern = r"(?<![A-Za-z0-9])" + re.escape(word.strip()) + r"(?![A-Za-z0-9])"
        return re.search(pattern, text, re.IGNORECASE) is not None
    return word in text


def classify(text: str) -> tuple[str, str]:
    """返回 (类别代码, 显示名)。没命中就是 OTHER。"""
    for code, label, words in CATEGORIES:
        if any(_contains(text, w) for w in words):
            return code, label
    return "OTHER", "📦 其他"


def detect_platform(text: str) -> str:
    for name, words in PLATFORMS:
        if any(w.lower() in text.lower() for w in words):
            return name
    return "其他平台"


def route_and_send(text: str, payload: dict | None = None, timeout: int = 10) -> str:
    """
    text:    用来判断类别的文字（推文正文 + 商品名 + 链接都拼进去最准）
    payload: 原本要发给 Discord 的 JSON（content / embeds 等）；不给就用 text 当 content
    返回命中的类别代码，方便打日志。
    """
    code, label = classify(text)
    platform = detect_platform(text)
    payload = dict(payload or {"content": text})

    # 在消息开头加上【平台】【类别】标签，全合集里也能一眼看出
    tag = f"【{platform}】【{label}】"
    payload["content"] = f"{tag}\n{payload.get('content', '')}".strip()

    targets = [os.getenv("WEBHOOK_ALL", "")]
    category_hook = os.getenv(ENV_KEY[code], "") or os.getenv("WEBHOOK_OTHER", "")
    targets.append(category_hook)

    sent = set()
    for url in targets:
        if not url or url in sent:
            continue
        sent.add(url)
        try:
            r = requests.post(url, json=payload, timeout=timeout)
            print(f"[{code}] Discord 推送 {r.status_code}")
        except Exception as e:
            print(f"[{code}] Discord 推送失败: {e}")
    return code


if __name__ == "__main__":
    # 本地自测：python category_router.py
    samples = [
        "【再販】ポケモンカードゲーム 拡張パック「熱風のアリーナ」BOX amazon.co.jp/dp/xxx",
        "楽天ブックス PS5 Pro 抽選販売開始",
        "Nintendo Switch 2 マリオカート ワールド セット 在庫復活 a.r10.to/abc",
        "ちいかわ ぬいぐるみ 予約開始 Amazon",
        "iPhone 17 Pro 256GB 在庫あり shopping.yahoo.co.jp",
        "サントリー 山崎 NV 700ml 定価販売",
        "Xbox Series X 値下げ",
        "ポケモン フィギュア 新作",
        "よくわからない商品",
    ]
    for s in samples:
        print(f"{classify(s)[1]:<10} {detect_platform(s):<6} | {s}")
