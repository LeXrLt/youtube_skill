# 📺 YouTube Subtitle Skill

一组 [OpenClaw](https://openclaw.ai/) skill：把 YouTube 频道的视频字幕抓取并存入
PostgreSQL 数据库，然后用自然语言查询这些数据。

本项目接入 `financial_hub` 共享数据库，程序状态、抓取进度与字幕数据全部同步到 PostgreSQL。

## 功能特点

- **数据入库**：字幕（含全文）、频道与视频元信息写入 `youtube_channels` / `youtube_videos`
- **状态/进度同步**：通过 `financial_hub_postgres` 上报 `crawl_runs` / `crawl_targets` /
  `system_events` / `component_status`，可在 Hub 中监控
- **断点续传**：已处理的视频会被跳过，重跑即续传
- **限流保护**：触发 HTTP 429 自动停止并保存进度
- **自然语言查询**：用一句话查频道、搜字幕、看统计

---

## 组成

| 文件 | 作用 |
|------|------|
| `SKILL.md` | 查询技能：用自然语言查询数据库（只读） |
| `SKILL_SETUP.md` | 安装技能：依赖安装、cookies 与环境初始化 |
| `main.py` | 爬虫入口：抓取字幕并写库（读写） |
| `scraper.py` | yt-dlp 抓取函数 |
| `db.py` / `schema.sql` / `config.py` | 数据库与配置 |
| `query_db.py` | 只读查询工具 |

---

## 安装

打开 OpenClaw，直接对它说：

> 请帮我安装这个 skill：https://github.com/LeXrLt/youtube_skill.git

随后让 OpenClaw 执行 **youtube-setup** 技能（`SKILL_SETUP.md`），它会：
1. 创建 Python 虚拟环境并安装依赖（yt-dlp、psycopg2、financial-hub-postgres 等）
2. 引导你配置 `.env`（PostgreSQL 连接信息，含只读用户）
3. 引导你配置 `cookies.txt`（YouTube 登录 cookies）
4. 初始化数据库表并验证连接

### 准备 Cookies（抓取时必需）

由于 YouTube 的反爬机制，抓取字幕需要登录 cookies：
1. 在 Chrome 安装 [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) 扩展
2. 打开 YouTube 并确保已登录
3. Cookie-Editor →「Export」→ 选择「Netscape」格式
4. 把导出内容保存为项目目录下的 `cookies.txt`

> 💡 出现 "Sign in to confirm you're not a bot" 报错说明 cookies 过期，重新导出即可。

---

## 抓取数据（写入数据库）

```bash
# 抓取单个频道
.venv/bin/python main.py --channel thu4878

# 抓取 crawl_targets 中所有启用的 youtube 目标
.venv/bin/python main.py
```

字幕按频道存放在 `subtitles/<频道名>/`（SRT），字幕全文同时写入数据库。

---

## 查询数据（自然语言）

安装并抓取后，直接用自然语言对 OpenClaw 提问：

| 你说 | 效果 |
|------|------|
| "看看数据库里抓了哪些 YouTube 频道" | 列出所有频道及视频数 |
| "搜索字幕里提到 transformer 的视频" | 全文搜索字幕 |
| "查 thu4878 频道最近 10 个视频" | 按频道筛选 |
| "查看 ID 为 42 的视频字幕全文" | 显示完整字幕 |
| "YouTube 数据库里有多少视频" | 统计概览 |

底层等价于：

```bash
.venv/bin/python query_db.py channels
.venv/bin/python query_db.py videos --search transformer
.venv/bin/python query_db.py videos --channel thu4878 --limit 10
.venv/bin/python query_db.py videos --id 42 --full
.venv/bin/python query_db.py stats
```

> 查询工具使用 `.env` 中的只读用户（`POSTGRES_READONLY_USER`），绝不修改数据。

---

## 常见问题

**Q: cookies 过期怎么办？**

重新用 Cookie-Editor 导出并覆盖 `cookies.txt` 即可。

**Q: 抓到一半被限流了？**

等 10~30 分钟后重跑 `main.py`，已处理的视频会自动跳过，从中断处续传。

**Q: 支持哪些语言的字幕？**

优先简体中文，其次英文，再次默认语言；完全无字幕会标记为 `no_subtitle`。

**Q: 数据存在哪里？**

频道存 `youtube_channels`，视频与字幕全文存 `youtube_videos`；抓取状态/进度同步到
`crawl_runs` / `crawl_targets` 等 Hub 表。

---

## 项目地址

https://github.com/LeXrLt/youtube_skill.git
