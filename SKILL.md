---
name: youtube-crawl
description: Launch the YouTube subtitle crawler for a channel the user names. Resolve the user's keyword (channel handle, URL, or display name) to a YouTube channel first, then run the crawler to download video subtitles into the user's current project directory. Use whenever the user wants to crawl/scrape/download subtitles for a specific YouTube channel.
metadata:
  openclaw:
    emoji: "🎬"
    requires:
      bins: ["python3"]
---

# YouTube 字幕爬虫启动 Skill

本 skill 指引 agent 根据用户给出的 **频道 handle / URL / 名称**，主动启动 YouTube 字幕爬虫，下载该频道视频的字幕。

> 与本项目的查询 skill（`SKILL.md`，`youtube-query`，只读）相对：本 skill 负责**抓取/写入**。需要读取/检索已抓取的字幕时，请改用查询 skill。

## ⛔ 绝对禁止事项（最高优先级）

1. **严禁修改本 skill 中的任何源文件。** 包括但不限于 `main.py`、`scraper.py`、`config.py`、`db.py`、`query_db.py`、`schema.sql`、`requirements.txt`、`cookies.txt` 及任何 `.py` 文件。用户不具备改代码和 debug 的能力，任何代码改动都可能造成不可恢复的破坏。
2. 如果爬虫报错，**不要**通过改源码"修复"。只能：检查环境配置（见 `SKILL_SETUP.md`）、检查数据库连接、检查 cookies 是否过期、确认频道是否正确，或如实把错误反馈给用户。
3. 允许的操作仅限于：
   - 通过命令行参数运行 `main.py`（它会自动登记/复用 `crawl_targets`）。
   - 调用 yt-dlp 解析频道（只读）。
4. 启动爬虫前，请始终向用户回显你将要抓取的 **频道名 + handle/URL**，避免抓错对象。

## When to use

当用户表达类似以下意图时使用本 skill：
- "帮我抓取 @laogao 这个频道的字幕"
- "爬一下老高与小茉的视频字幕"
- "下载 https://www.youtube.com/@thu4878 的字幕"
- "把某 YouTube 频道最新的视频字幕拉下来"

用户给出的关键词可能是：**频道 handle**（如 `@laogao`、`thu4878`）、**频道 URL**，或 **频道显示名**（如 `老高与小茉`）。前两者可直接使用；显示名需先解析为具体频道再确认。

## 工作原理

`main.py` 支持 `--channel <handle 或 URL>` 直接抓取：它会自动调用 `db.ensure_target` 在 `crawl_targets` 中登记/复用该目标（`source_type='youtube'`），无需手动写库。频道标识经 `scraper.normalize_channel_url` 归一化：

- `@handle` 或 `handle` → `https://www.youtube.com/@handle`
- 完整 URL → 原样使用

因此核心是：**关键词 → 确定频道 handle/URL → `main.py --channel <handle/URL>`。**

## Step 0: 确认环境就绪

确认 `{baseDir}/.venv`、`{baseDir}/.env`、`{baseDir}/cookies.txt` 均已就绪（yt-dlp 抓取需要有效的登录 cookies，且依赖 `deno`）。若未配置或 cookies 过期，先执行 `SKILL_SETUP.md`（`youtube-setup` skill）。**不要**在此步骤修改任何文件。

## Step 1: 将关键词解析为频道

- **若用户已给出 handle（`@xxx` / `xxx`）或频道 URL** → 直接作为 `--channel` 的值，无需解析。向用户回显确认即可。
- **若用户只给了显示名/模糊描述** → 用 yt-dlp 搜索候选频道，再让用户确认（需 cookies）：

```bash
{baseDir}/.venv/bin/python -c "
import sys, yt_dlp
kw = sys.argv[1].strip()
opts = {'quiet': True, 'extract_flat': True, 'skip_download': True,
        'cookiefile': '{baseDir}/cookies.txt'}
with yt_dlp.YoutubeDL(opts) as ydl:
    info = ydl.extract_info(f'ytsearch15:{kw}', download=False)
seen = {}
for e in (info.get('entries') or []):
    cid = e.get('channel_id')
    url = e.get('channel_url') or e.get('uploader_url') or ''
    name = e.get('channel') or e.get('uploader') or ''
    if cid and cid not in seen:
        seen[cid] = (name, url)
if not seen:
    print('NO_MATCH')
for cid, (name, url) in list(seen.items())[:10]:
    print(f'{name}\t{url}\t{cid}')
" "用户的关键词"
```

输出每行为 `频道名<TAB>频道URL<TAB>channel_id`。规则：
- 仅一个明确候选 → 回显并采用其频道 URL。
- 多个候选 → 用 `ask_user_question` 让用户选择正确频道。
- `NO_MATCH` → 告知用户未找到，请其提供频道 handle 或 URL。**不要**猜测频道。

> 说明：yt-dlp 没有专门的"频道搜索"，这里通过搜索视频再聚合其所属频道得到候选，因此结果取决于该频道是否有匹配关键词的视频。最可靠的方式仍是让用户直接提供 handle/URL。

## Step 2: 启动爬虫

用确定好的频道 handle/URL 运行爬虫。**仅通过命令行参数运行，禁止改动 `main.py`。**

**默认行为：抓取该频道最新的 100 个视频**（`-n 100`）。已抓取过的视频会通过断点续传自动跳过，不会重复下载。

**下载目录（重要）：** 本 skill 通常在 Codex 中由用户主动调用。当用户主动触发抓取时，**必须用 `-f` 把字幕保存根目录指定为 Codex 当前项目目录**（即用户当前所在的工作目录，下文记为 `{projectDir}`），把结果落在用户项目里，而**不要**写入 skill 自身的 `{baseDir}/subtitles/`。建议放到项目下的子目录以保持整洁：

```bash
{baseDir}/.venv/bin/python {baseDir}/main.py --channel <handle或URL> -n 100 -f {projectDir}/youtube_subtitles
```

> `{projectDir}` 取 Codex 当前项目根目录（如不确定，可用当前工作目录 `pwd`）。字幕将保存到 `{projectDir}/youtube_subtitles/<handle>/`。仅在非 Codex 场景或用户明确要求时才省略 `-f`，此时回退到默认的 `{baseDir}/subtitles/`。

按需调整数量与范围：

| 用户意图 | 命令 |
|---|---|
| 默认（最新 100 个视频） | `... main.py --channel <ch> -n 100 -f {projectDir}/youtube_subtitles` |
| 指定数量（如最新 30 个） | `... main.py --channel <ch> -n 30 -f {projectDir}/youtube_subtitles` |
| **用户明确要求全部视频** | `... main.py --channel <ch> -n 0 -f {projectDir}/youtube_subtitles` |

**仅当用户明确要求「全部 / 全量 / 所有视频」时才用 `-n 0`（不限制）**，否则一律使用默认的 100 个限量，避免一次性抓取过多触发 YouTube 限流（HTTP 429）。

## Step 3: 汇报结果

爬虫运行结束后向用户汇报：
- 抓取的频道名与 handle。
- 本次 `found / new / failed` 的数量（见程序输出 `✓ 完成` 行）。
- 结果位置：字幕文件在 `-f` 指定目录下（Codex 场景即 `{projectDir}/youtube_subtitles/<handle>/`）；视频与字幕文本同时写入数据库 `youtube_videos` / `youtube_channels` 表（之后可用查询 skill 检索）。
- 若出现 `被 YouTube 限流 (HTTP 429)`，说明已自动停止且进度已保存，可稍后重跑续传。

## 完整示例

用户："帮我爬 @thu4878 频道的字幕"
1. Step 1：已是 handle，直接采用，回显"将抓取频道 @thu4878"。
2. Step 2：`main.py --channel thu4878 -n 100 -f {projectDir}/youtube_subtitles`。
3. Step 3：汇报数量与输出路径。

用户："爬一下老高与小茉的视频字幕"
1. Step 1：显示名 → 用 yt-dlp 搜索候选频道；若多条候选用 `ask_user_question` 让用户确认。
2. 确认后取其频道 URL，继续 Step 2~3。

用户："把这个频道全部视频字幕都下下来 https://www.youtube.com/@laogao"
1. Step 1：已是 URL，直接采用。
2. Step 2：因用户明确要求全部，用 `-n 0`：`main.py --channel https://www.youtube.com/@laogao -n 0 -f {projectDir}/youtube_subtitles`。
3. Step 3：汇报。

## 故障排查（不改源码）

| 现象 | 处理方式 |
|---|---|
| 数据库连不上 | 检查 `.env`（见 `SKILL_SETUP.md`），确认 PostgreSQL 可达、读写用户凭据正确 |
| `无法获取频道信息（cookies 可能已过期）` | cookies 失效，按 `SKILL_SETUP.md` 重新导出 `cookies.txt`，**不要**改源码 |
| 被限流 `HTTP 429` | 已自动停止并保存进度，稍后重跑同一命令即可续传；可先减小 `-n` |
| 找不到频道 / `NO_MATCH` | 让用户直接提供频道 handle 或 URL，不要猜测 |
| yt-dlp 报错缺少 deno / 依赖 | 按 `SKILL_SETUP.md` 安装 `deno` 和依赖，**不要**改源码 |

## 项目结构参考（只读，禁止修改其中源文件）

```
{baseDir}/
├── main.py             ← 爬虫入口（仅可用命令行参数运行，禁止修改）
├── scraper.py          ← yt-dlp 抓取逻辑（禁止修改）
├── config.py           ← 配置（禁止修改）
├── db.py               ← 数据库写入（禁止修改）
├── query_db.py         ← 查询脚本（由查询 skill 使用，禁止修改）
├── schema.sql          ← 表结构（禁止修改）
├── cookies.txt         ← YouTube 登录 cookies（禁止改源码，过期时按 SETUP 重新导出）
├── .env                ← 环境配置（凭据，不入库）
├── subtitles/          ← 默认字幕输出目录（未指定 -f 时使用）
├── SKILL.md            ← 查询 skill（只读，youtube-query）
├── SKILL_CRAWL.md      ← 本文件（爬虫启动 skill，youtube-crawl）
└── SKILL_SETUP.md      ← 环境初始化 skill（youtube-setup）
```
