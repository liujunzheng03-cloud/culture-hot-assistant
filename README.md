# 每日文化热点微信汇报助手

专门解决**“每天中午1点前向主任汇报 3 个当日文化相关热点、热搜”**的全自动工具。

## 功能亮点
1. **无需爬虫 Key，内置 6 大平台实时热榜**：自动拉取 **微博、百度、抖音、今日头条、澎湃新闻、B站** 共约 160+ 条实时热搜。
2. **DeepSeek 智能精选与润色**：
   - 自动挑出 **3 条主推文化热点 + 2 条备选文化热点**（涵盖文旅非遗、文博考古、影视文艺、青年与社会文化现象）。
   - 生成**【微信直接复制版】**纯文本（无多余符号，长按复制即可直接发给邢主任）。
   - 附带**【防追问背景小抄】**与原热搜直达链接，主任追问细节也能对答如流。
3. **零成本全自动运行**：通过 GitHub Actions 每天中午 **11:45~12:00** 自动推送到她的手机微信。

---

## 你需要准备的 2 个配置（3 分钟搞定）

### 1. DeepSeek API Key
- 前往 [DeepSeek 开放平台](https://platform.deepseek.com/api_keys) 创建一个 API Key（新号或充 10 块钱够用好几年，每天调用一次仅消耗约 0.002 元）。

### 2. PushPlus 微信推送 Token（免费，用来发到她微信）
1. 用你自己的微信扫码登录 [PushPlus 官网 (pushplus.plus)](https://www.pushplus.plus/)。
2. 点击顶部菜单 **【一对一推送】**，复制你的 `Token`（对应 `PUSHPLUS_TOKEN`）。
3. **怎么发给她？**
   - 点击菜单 **【一对多推送】** $\rightarrow$ 创建一个群组（例如填群组编码 `culture_hot`，名称填“每日文化热搜”）。
   - 创建后会生成一个**专属微信二维码**。
   - **你只要把这个二维码截图发给她，让她用微信扫一下关注公众号**，以后每天中午她就会在微信里收到排好版的汇报消息！

---

## 部署到 GitHub 实现每天自动运行

1. 在你的 GitHub 上新建一个仓库（公开或私有均可），将本文件夹内的文件上传上去。
2. 进入仓库的 **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions** $\rightarrow$ 点击 **New repository secret**，添加以下变量：
   - `DEEPSEEK_API_KEY`：填你的 DeepSeek API Key（必填）
   - `PUSHPLUS_TOKEN`：填你在 PushPlus 复制的 Token（必填）
   - `PUSHPLUS_TOPIC`：填你在 PushPlus 创建的群组编码，如 `culture_hot`（如果你只推给自己测试，可不填）
3. 进入仓库顶部的 **Actions** 标签页，点击左侧的 **每日文化热点微信推送** $\rightarrow$ 点击右侧 **Run workflow** 即可立即测试推送一次！

---

## 本地电脑直接测试运行

在终端（PowerShell）中执行：

```powershell
$env:DEEPSEEK_API_KEY="sk-你的deepseek密钥"
$env:PUSHPLUS_TOKEN="你的pushplus_token"
python d:\Antigravity\culture-hot-assistant\main.py
```

运行后还会自动在同目录下生成 `latest_report.html`，双击即可在浏览器里预览微信推送卡片效果。
