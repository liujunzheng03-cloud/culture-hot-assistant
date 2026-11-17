import os
import sys
import json
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import datetime
from urllib.parse import quote
import requests

# 设置标准输出编码为 UTF-8，防止 Windows 控制台打印 emoji 报错
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://s.weibo.com/",
}


def fetch_weibo_hot(limit=35):
    """抓取微博实时热搜榜"""
    url = "https://weibo.com/ajax/statuses/hot_band"
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        band_list = resp.json().get("data", {}).get("band_list", [])
        for item in band_list:
            word = item.get("word", "").strip()
            if not word or item.get("is_ad"):
                continue
            category = item.get("category", "")
            note = f"（分类：{category}）" if category else ""
            items.append({"platform": "微博热搜", "title": word, "desc": note})
            if len(items) >= limit:
                break
    except Exception as e:
        print(f"[警告] 微博热搜抓取失败: {e}")
    return items


def fetch_baidu_hot(limit=35):
    """抓取百度实时热搜榜（含摘要描述）"""
    url = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        cards = resp.json().get("data", {}).get("cards", [])
        if cards and cards[0].get("content"):
            sub_list = cards[0]["content"][0].get("content", [])
            for item in sub_list:
                word = item.get("word", "").strip()
                desc = item.get("desc", "").strip()
                if not word:
                    continue
                items.append({
                    "platform": "百度热搜",
                    "title": word,
                    "desc": desc[:80] if desc else "",
                })
                if len(items) >= limit:
                    break
    except Exception as e:
        print(f"[警告] 百度热搜抓取失败: {e}")
    return items


def fetch_douyin_hot(limit=35):
    """抓取抖音热点榜"""
    url = "https://www.iesdouyin.com/web/api/v2/hotsearch/billboard/word/"
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        word_list = resp.json().get("word_list", [])
        for item in word_list[:limit]:
            word = item.get("word", "").strip()
            if word:
                items.append({"platform": "抖音热榜", "title": word, "desc": ""})
    except Exception as e:
        print(f"[警告] 抖音热榜抓取失败: {e}")
    return items


def fetch_toutiao_hot(limit=30):
    """抓取今日头条热榜"""
    url = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json().get("data", [])
        for item in data[:limit]:
            title = item.get("Title", "").strip()
            label = item.get("ClusterType", "")
            if title:
                items.append({"platform": "今日头条", "title": title, "desc": str(label)})
    except Exception as e:
        print(f"[警告] 今日头条抓取失败: {e}")
    return items


def fetch_thepaper_hot(limit=20):
    """抓取澎湃新闻热榜（偏深度与人文社科）"""
    url = "https://cache.thepaper.cn/contentapi/wwwIndex/rightSidebar"
    items = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        hot_news = resp.json().get("data", {}).get("hotNews", [])
        for item in hot_news[:limit]:
            name = item.get("name", "").strip()
            node_name = item.get("nodeInfo", {}).get("name", "")
            if name:
                items.append({
                    "platform": "澎湃新闻",
                    "title": name,
                    "desc": f"栏目：{node_name}" if node_name else "",
                })
    except Exception as e:
        print(f"[警告] 澎湃新闻抓取失败: {e}")
    return items


def fetch_bilibili_hot(limit=25):
    """抓取B站热搜榜（偏青年文化、二次元、科普人文）"""
    url = "https://app.bilibili.com/x/v2/search/trending/ranking"
    items = []
    try:
        bili_headers = {"User-Agent": HEADERS["User-Agent"]}
        resp = requests.get(url, headers=bili_headers, timeout=10)
        b_list = resp.json().get("data", {}).get("list", [])
        for item in b_list[:limit]:
            word = item.get("show_name", "").strip()
            if word:
                items.append({"platform": "B站热搜", "title": word, "desc": ""})
    except Exception as e:
        print(f"[警告] B站热搜抓取失败: {e}")
    return items


def collect_all_hot_topics():
    """聚合多平台热搜并去重"""
    all_raw = []
    all_raw.extend(fetch_weibo_hot())
    all_raw.extend(fetch_baidu_hot())
    all_raw.extend(fetch_douyin_hot())
    all_raw.extend(fetch_toutiao_hot())
    all_raw.extend(fetch_thepaper_hot())
    all_raw.extend(fetch_bilibili_hot())

    seen = set()
    deduped = []
    for item in all_raw:
        title = item["title"]
        if title in seen:
            continue
        seen.add(title)
        deduped.append(item)

    print(f"[信息] 共抓取并去重得到 {len(deduped)} 条全网实时热搜。")
    return deduped


def generate_culture_report_with_deepseek(hot_items, api_key, base_url=None, model=None):
    """调用 DeepSeek API 筛选文化热点并生成可直接复制的汇报文案"""
    api_base = (base_url or os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").rstrip("/")
    model_name = model or os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
    today_str = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).strftime("%Y年%m月%d日")

    hot_text_lines = []
    for idx, item in enumerate(hot_items, 1):
        desc_part = f" | 简介/标签：{item['desc']}" if item.get("desc") else ""
        hot_text_lines.append(f"{idx}. [{item['platform']}] {item['title']}{desc_part}")
    hot_list_str = "\n".join(hot_text_lines)

    system_prompt = (
        "你是一位资深文化宣传与传媒部门的得力助手。"
        "用户每天中午1点前需要向领导（邢主任）微信汇报 3 个当天与【文化】相关的热点或热搜。\n"
        "这里的“文化相关”采用广义但有价值的标准，优先级从高到低包括：\n"
        "1. 传统文化、非遗民俗、博物馆/考古文博、历史古迹、传统节气与礼仪\n"
        "2. 地方文旅出圈、城市文化名片、特色文化活动\n"
        "3. 图书文学、电影电视剧、纪录片、综艺、戏剧演出、音乐美术、动漫游戏中的文化现象\n"
        "4. 语言文字梗、青年文化趋势、教育与读书、中西文化交流、极具讨论度的社会文化观念碰撞\n\n"
        "请你从提供的今日实时热搜列表中，精选出 **3个主推文化热点** + **2个备选文化热点**（共5个，尽量覆盖不同维度，避免同质化）。\n"
        "严格输出 JSON 格式，不要输出任何额外解释文字。JSON 结构如下：\n"
        "{\n"
        '  "wechat_ready_text": "一段可以直接全选复制发给主任的微信纯文本（开头带自然礼貌的问候，如：主任中午好，今日关注的3个文化相关热点如下：\\n\\n1. 【热点词】（平台）\\n简况与看点：用50~70字自然流畅地说清是什么事、有什么文化看点。\\n\\n2. ...\\n\\n3. ...\\n注意：这段纯文本内绝不能出现 Markdown 星号 ** 或 # 号，保证复制到微信对话框里干净自然！）",\n'
        '  "main_picks": [\n'
        '    {\n'
        '      "title": "热搜原词",\n'
        '      "platform": "来源平台",\n'
        '      "category": "文化细分维度（如：文旅非遗 / 影视文艺 / 社会文化现象）",\n'
        '      "report_copy": "单条汇报话术（纯文本，方便单独复制替换）",\n'
        '      "background_note": "给汇报人自己看的背景小抄（80字左右，讲清楚来龙去脉，防止主任追问时答不上来）"\n'
        "    }\n"
        "  ],\n"
        '  "backup_picks": [\n'
        "    // 结构同 main_picks，共 2 条备选，万一用户觉得主推里有某条不够好，可以随时拿备选替换\n"
        "  ]\n"
        "}"
    )

    user_prompt = f"今天是 {today_str}。以下是刚刚抓取的全网各平台实时热搜列表：\n\n{hot_list_str}"

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.5,
        "response_format": {"type": "json_object"},
    }

    resp = requests.post(
        f"{api_base}/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"DeepSeek API 调用失败 ({resp.status_code}): {resp.text}")

    content = resp.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def build_html_message(report_data):
    """构建适合手机微信点开阅读与一键复制的精美 HTML 消息内容"""
    today_str = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).strftime("%m月%d日")
    wechat_text = report_data.get("wechat_ready_text", "")
    main_picks = report_data.get("main_picks", [])
    backup_picks = report_data.get("backup_picks", [])

    def render_cards(picks, badge_color):
        cards_html = []
        for idx, item in enumerate(picks, 1):
            title = item.get("title", "")
            platform = item.get("platform", "")
            category = item.get("category", "文化热点")
            report_copy = item.get("report_copy", "")
            bg_note = item.get("background_note", "")
            search_url = f"https://m.baidu.com/s?word={quote(title)}"
            cards_html.append(f"""
            <div style="background:#ffffff;border:1px solid #eaeaea;border-radius:10px;padding:14px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,0.04);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
                    <span style="background:{badge_color};color:#fff;font-size:12px;padding:2px 8px;border-radius:4px;font-weight:bold;">
                        {idx}. {category} · {platform}
                    </span>
                    <a href="{search_url}" style="font-size:12px;color:#2563eb;text-decoration:none;">查看原热搜 &rarr;</a>
                </div>
                <div style="font-size:16px;font-weight:bold;color:#111827;margin-bottom:8px;">{title}</div>
                <div style="background:#f8fafc;border-left:3px solid {badge_color};padding:8px 10px;font-size:13px;color:#334155;margin-bottom:8px;line-height:1.6;">
                    <strong>单条汇报话术：</strong><br>{report_copy}
                </div>
                <div style="font-size:12px;color:#64748b;line-height:1.5;">
                    💡 <strong>防追问背景小抄：</strong>{bg_note}
                </div>
            </div>
            """)
        return "\n".join(cards_html)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{today_str} 文化热点汇报助手</title>
</head>
<body style="margin:0;padding:12px;background:#f3f4f6;">
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;color:#1f2937;max-width:600px;margin:0 auto;padding:4px;">
        <div style="background:linear-gradient(135deg,#059669,#10b981);color:white;padding:16px;border-radius:12px;margin-bottom:16px;">
            <div style="font-size:18px;font-weight:bold;">🎨 {today_str} 文化热点汇报助手</div>
            <div style="font-size:12px;opacity:0.9;margin-top:4px;">已从今日微博、百度、抖音、头条、澎湃、B站热榜中精选</div>
        </div>

        <div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:10px;padding:14px;margin-bottom:18px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
                <span style="font-size:14px;font-weight:bold;color:#065f46;">
                    📋 【直接复制版】发给邢主任：
                </span>
                <button onclick="copyReport()" id="copyBtn" style="background:#059669;color:#ffffff;border:none;border-radius:6px;padding:6px 14px;font-size:13px;font-weight:bold;cursor:pointer;">
                    一键复制全文
                </button>
            </div>
            <div id="reportText" style="background:#ffffff;border:1px dashed #34d399;border-radius:8px;padding:12px;font-size:14px;color:#111827;line-height:1.7;white-space:pre-wrap;user-select:all;">{wechat_text}</div>
        </div>

        <h3 style="font-size:15px;color:#0f172a;margin:16px 0 10px 0;">🔥 今日主推 3 条（含防追问背景小抄）</h3>
        {render_cards(main_picks, "#059669")}

        <h3 style="font-size:15px;color:#0f172a;margin:18px 0 10px 0;">🔄 备选 2 条（若上面有不喜欢的，可复制下面替换）</h3>
        {render_cards(backup_picks, "#6366f1")}
    </div>
    <script>
    function copyReport() {{
        const text = document.getElementById('reportText').innerText;
        navigator.clipboard.writeText(text).then(() => {{
            const btn = document.getElementById('copyBtn');
            btn.innerText = '✅ 已复制！可直接去微信粘贴';
            btn.style.background = '#047857';
            setTimeout(() => {{
                btn.innerText = '一键复制全文';
                btn.style.background = '#059669';
            }}, 3000);
        }});
    }}
    </script>
</body>
</html>"""
    return html


def send_email_to_wechat(title, html_content, smtp_user, smtp_pass, receiver_email, smtp_host=None):
    """通过免费邮箱发送（对方在微信开启'QQ邮箱提醒'即可在微信内直接弹窗收到）"""
    if not smtp_host:
        if "@qq.com" in smtp_user:
            smtp_host = "smtp.qq.com"
        elif "@163.com" in smtp_user:
            smtp_host = "smtp.163.com"
        else:
            smtp_host = "smtp.qq.com"

    msg = MIMEText(html_content, "html", "utf-8")
    msg["From"] = smtp_user
    msg["To"] = receiver_email
    msg["Subject"] = Header(title, "utf-8")

    with smtplib.SMTP_SSL(smtp_host, 465, timeout=15) as server:
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [receiver_email], msg.as_string())
    print(f"[成功] 已发送至 {receiver_email}（微信QQ邮箱提醒将直接弹窗）！")


def send_pushplus(title, html_content, token, topic=None):
    """通过 PushPlus 推送到微信（支持单人或一对多群组二维码订阅）"""
    url = "http://www.pushplus.plus/send"
    payload = {
        "token": token,
        "title": title,
        "content": html_content,
        "template": "html",
    }
    if topic:
        payload["topic"] = topic

    resp = requests.post(url, json=payload, timeout=15)
    res_json = resp.json()
    if res_json.get("code") == 200:
        print(f"[成功] PushPlus 微信推送成功！流水号: {res_json.get('data')}")
    else:
        print(f"[错误] PushPlus 推送返回异常: {res_json}")


def main():
    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    pushplus_token = os.getenv("PUSHPLUS_TOKEN", "").strip()
    pushplus_topic = os.getenv("PUSHPLUS_TOPIC", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASS", "").strip()
    receiver_email = os.getenv("RECEIVER_EMAIL", "").strip()

    print("=== Step 1: 正在抓取全网多平台实时热搜 ===")
    hot_items = collect_all_hot_topics()
    if not hot_items:
        raise RuntimeError("未能抓取到任何平台的热搜数据，请检查网络连接。")

    if not deepseek_key:
        print("\n[提示] 未检测到环境变量 DEEPSEEK_API_KEY，仅展示抓取到的前 15 条热搜预览：")
        for idx, item in enumerate(hot_items[:15], 1):
            print(f"  {idx}. [{item['platform']}] {item['title']}")
        print("\n请配置环境变量 DEEPSEEK_API_KEY 后重新运行。")
        return

    print("=== Step 2: 正在调用 DeepSeek 筛选文化热点并生成汇报话术 ===")
    report_data = generate_culture_report_with_deepseek(hot_items, deepseek_key)

    print("\n================ 微信直接复制版预览 ================")
    print(report_data.get("wechat_ready_text", ""))
    print("====================================================\n")

    html_content = build_html_message(report_data)

    # 保存本地预览文件及 GitHub Pages 首页文件 index.html
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for filename in ("latest_report.html", "index.html"):
        file_path = os.path.join(base_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
    print(f"[信息] 已生成网页文件: {os.path.join(base_dir, 'latest_report.html')}")

    today_str = datetime.datetime.now(
        datetime.timezone(datetime.timedelta(hours=8))
    ).strftime("%m月%d日")
    push_title = f"【{today_str}】今日3条文化热点汇报已生成"

    if smtp_user and smtp_pass and receiver_email:
        print("=== Step 3: 正在通过免费邮箱推送到微信（QQ邮箱提醒） ===")
        send_email_to_wechat(push_title, html_content, smtp_user, smtp_pass, receiver_email)

    if pushplus_token:
        print("=== Step 3: 正在通过 PushPlus 推送到手机微信 ===")
        send_pushplus(push_title, html_content, pushplus_token, pushplus_topic or None)

    if not (smtp_user and smtp_pass and receiver_email) and not pushplus_token:
        print("[提示] 未配置推送参数，已生成本地/在线网页版（含一键复制按钮）。")


if __name__ == "__main__":
    main()
