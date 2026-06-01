---
name: youtube-query
description: Query YouTube channels and video subtitles stored in the local PostgreSQL database using natural language. Search videos by channel, keyword, or status; list channels; view full subtitle text; and see statistics. Read-only — no data modification.
metadata:
  openclaw:
    emoji: "📺"
    requires:
      bins:
        - python3
---

# YouTube Subtitle Database Query Skill

This skill answers natural-language questions about YouTube videos and their
subtitles that have been previously crawled and stored in a PostgreSQL database
(`youtube_channels` and `youtube_videos` tables).

**This skill is strictly read-only. It never inserts, updates, or deletes any data.**

## When to use

Use this skill when the user wants to:
- Read or search YouTube video subtitles from the database
- List channels that have been crawled
- Find videos by channel, keyword, or status
- View the full subtitle text of a specific video
- Get statistics on crawled YouTube content

Do **NOT** use this skill when the user wants to crawl/download new subtitles from
YouTube (that is the crawler workflow in `main.py`).

If the database is not yet set up (no `.venv/` or `.env`, or connection errors),
run the **`youtube-setup`** skill (`SKILL_SETUP.md`) first.

## How to use

Translate the user's natural-language request into one of the commands below.
All commands share the same base invocation:

```bash
{baseDir}/.venv/bin/python {baseDir}/query_db.py <command> [options]
```

### 1. List channels

```bash
{baseDir}/.venv/bin/python {baseDir}/query_db.py channels
```

Returns every channel that has videos, with video counts and subtitle counts.

### 2. Query videos

```bash
{baseDir}/.venv/bin/python {baseDir}/query_db.py videos [options]
```

Options:
- `--channel HANDLE_OR_ID` — Filter by channel handle (e.g. `thu4878`) or channel ID
- `--search KEYWORD` — Search in title and subtitle full text (case-insensitive)
- `--status STATUS` — Filter by status (`success`, `no_subtitle`, `skipped`, `error`)
- `--limit N` — Max results (default: 20, max: 500)
- `--offset N` — Skip first N results (for pagination)
- `--id ID` — Fetch a single video by its database ID
- `--full` — Show complete subtitle text instead of preview

### 3. View statistics

```bash
{baseDir}/.venv/bin/python {baseDir}/query_db.py stats [--channel HANDLE_OR_ID]
```

Returns total channel/video counts and a breakdown by status.

## Output format

Each video is output in a stable structured format:

```
ID: <id>
标题: <title>
来源: youtube
频道: <channel title>
视频ID: <video_id>
原始链接: <video_url>
字幕语言: <subtitle_lang>
状态: <status>
本地字幕: <subtitle_path>     (if present)
字幕预览: <first 200 chars>   (default)
--- 字幕全文 ---             (with --full flag)
<full subtitle text>
```

Videos are separated by `============` lines.

## Examples

User says: "看看数据库里抓了哪些YouTube频道"
→ Run: `{baseDir}/.venv/bin/python {baseDir}/query_db.py channels`

User says: "搜索YouTube字幕里提到 transformer 的视频"
→ Run: `{baseDir}/.venv/bin/python {baseDir}/query_db.py videos --search transformer`

User says: "查 thu4878 频道最近10个视频"
→ Run: `{baseDir}/.venv/bin/python {baseDir}/query_db.py videos --channel thu4878 --limit 10`

User says: "查看ID为42的视频字幕全文"
→ Run: `{baseDir}/.venv/bin/python {baseDir}/query_db.py videos --id 42 --full`

User says: "哪些视频没有字幕"
→ Run: `{baseDir}/.venv/bin/python {baseDir}/query_db.py videos --status no_subtitle`

User says: "YouTube数据库里有多少视频"
→ Run: `{baseDir}/.venv/bin/python {baseDir}/query_db.py stats`

User says: "看看 laogao 频道的统计"
→ Run: `{baseDir}/.venv/bin/python {baseDir}/query_db.py stats --channel laogao`

## Setup

This skill shares the virtual environment and `.env` with the YouTube crawler.
If the environment is missing, run the `youtube-setup` skill (`SKILL_SETUP.md`).
Database connection is configured via `{baseDir}/.env` (read-only user).
