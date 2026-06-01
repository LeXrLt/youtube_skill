---
name: youtube-setup
description: Install dependencies and configure environment variables for the YouTube skill project. Run this before using the YouTube query or crawler skills.
metadata:
  openclaw:
    emoji: "🛠️"
    requires:
      bins: ["python3"]
---

# YouTube 项目环境配置 Skill

本 skill 指引 agent 完成项目依赖安装、cookies 配置和环境变量配置，确保其他 skill
（查询、爬虫）可以正常运行。

**本 skill 不涉及数据操作，仅做环境初始化。**

## When to use

Use this skill when:
- The project is freshly cloned and has not been set up yet
- The virtual environment `.venv/` does not exist
- The `.env` file does not exist
- `cookies.txt` is missing or expired
- The user explicitly asks to install or set up the project
- Other skills fail due to missing dependencies or missing `.env`

## Step 1: Create virtual environment

Check if `{baseDir}/.venv` exists. If not, create it:

```bash
python3 -m venv {baseDir}/.venv
```

## Step 2: Install Python dependencies

```bash
{baseDir}/.venv/bin/pip install -r {baseDir}/requirements.txt
```

Key dependencies (defined in `requirements.txt`):
- `yt-dlp` — YouTube downloader used to fetch subtitles
- `psycopg2-binary` — PostgreSQL driver
- `python-dotenv` — Load `.env` config
- `financial-hub-postgres` — Shared database client library (crawl lifecycle reporting)

> 💡 yt-dlp 需要 `deno`（部分 YouTube JS challenge 求解依赖）。若运行字幕抓取时报错，
> 提示用户安装 deno：`curl -fsSL https://deno.land/install.sh | sh`（脚本会自动把
> `~/.deno/bin` 加入 PATH）。

## Step 3: Configure environment variables

Check if `{baseDir}/.env` exists. If not, copy from the example file:

```bash
cp {baseDir}/.env.example {baseDir}/.env
```

Then ask the user to fill in the actual values. The variables are:

| Variable | Description | Example |
|---|---|---|
| `POSTGRES_HOST` | PostgreSQL server address | `127.0.0.1` |
| `POSTGRES_PORT` | PostgreSQL server port | `5432` |
| `POSTGRES_USER` | Database user (for crawler, read-write) | `hub_user` |
| `POSTGRES_PASSWORD` | Password for the read-write user | `hub_password` |
| `POSTGRES_DB` | Database name | `financial_hub` |
| `POSTGRES_READONLY_USER` | Database user (for query skill, read-only) | `hub_readonly` |
| `POSTGRES_READONLY_PASSWORD` | Password for the read-only user | `hub_password` |

**Important:** The `.env` file contains sensitive credentials and is already in `.gitignore`. Never commit it to version control.

## Step 4: Configure YouTube cookies

Subtitle crawling requires logged-in YouTube cookies to bypass anti-bot checks.

Check if `{baseDir}/cookies.txt` exists. If not, guide the user:
1. Install the [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) browser extension.
2. Open YouTube and make sure they are logged in.
3. Click Cookie-Editor → Export → choose **Netscape** format.
4. Save the exported content as `{baseDir}/cookies.txt`.

> `cookies.txt` is in `.gitignore` and must never be committed. If crawling later
> reports "Sign in to confirm you're not a bot", the cookies have expired and need
> to be re-exported.

## Step 5: Initialize database tables

The crawler creates the `youtube_channels` and `youtube_videos` tables automatically
on first run via `schema.sql`. To initialize them explicitly (using the read-write user):

```bash
{baseDir}/.venv/bin/python -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv('{baseDir}/.env')
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST', '127.0.0.1'),
    port=int(os.getenv('POSTGRES_PORT', '5432')),
    user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'),
    dbname=os.getenv('POSTGRES_DB'),
)
with open('{baseDir}/schema.sql', 'r', encoding='utf-8') as f:
    conn.cursor().execute(f.read())
conn.commit()
conn.close()
print('Schema initialized: youtube_channels, youtube_videos')
"
```

## Step 6: Verify setup

Run the query tool to verify the read-only database connection is working:

```bash
{baseDir}/.venv/bin/python {baseDir}/query_db.py stats
```

If this command prints statistics without errors, the setup is complete.

If it fails with a connection error, ask the user to check:
1. Is PostgreSQL running and accessible at the configured host/port?
2. Are the database credentials correct?
3. Does the database and the readonly user exist?

## Step 7: Create readonly database user (if needed)

If Step 6 fails because the `hub_readonly` user does not exist, create it by running:

```bash
{baseDir}/.venv/bin/python -c "
import psycopg2, os
from dotenv import load_dotenv
load_dotenv('{baseDir}/.env')
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST', '127.0.0.1'),
    port=int(os.getenv('POSTGRES_PORT', '5432')),
    user=os.getenv('POSTGRES_USER'),
    password=os.getenv('POSTGRES_PASSWORD'),
    dbname=os.getenv('POSTGRES_DB'),
)
conn.autocommit = True
cur = conn.cursor()
ro_user = os.getenv('POSTGRES_READONLY_USER', 'hub_readonly')
ro_pass = os.getenv('POSTGRES_READONLY_PASSWORD', 'hub_password')
cur.execute(f\"CREATE ROLE {ro_user} WITH LOGIN PASSWORD '{ro_pass}'\")
cur.execute(f'GRANT CONNECT ON DATABASE {os.getenv(\"POSTGRES_DB\")} TO {ro_user}')
cur.execute(f'GRANT USAGE ON SCHEMA public TO {ro_user}')
cur.execute(f'GRANT SELECT ON ALL TABLES IN SCHEMA public TO {ro_user}')
cur.execute(f'ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {ro_user}')
cur.close()
conn.close()
print(f'Created readonly user: {ro_user}')
"
```

Then re-run Step 6 to verify.

## Running the crawler (to populate data)

Once setup is complete, crawl a channel's subtitles into the database:

```bash
{baseDir}/.venv/bin/python {baseDir}/main.py --channel thu4878
```

Or crawl all enabled `source_type='youtube'` targets from `crawl_targets`:

```bash
{baseDir}/.venv/bin/python {baseDir}/main.py
```

Crawl state and progress are synced to `crawl_runs` / `crawl_targets` /
`system_events` / `component_status` via `financial_hub_postgres`. The crawler is
resumable — re-running skips videos already processed.

## Examples

User says: "帮我安装YouTube技能的依赖"
→ Execute Step 1 and Step 2.

User says: "配置YouTube项目的环境变量"
→ Execute Step 3, then ask the user for actual database credentials.

User says: "配置YouTube cookies"
→ Execute Step 4.

User says: "初始化YouTube项目"
→ Execute Step 1 through Step 6.

User says: "YouTube查询工具连不上数据库"
→ Check `.env` is present and correct (Step 3), then run Step 6 to diagnose. If readonly user missing, run Step 7.

## Project structure reference

```
{baseDir}/
├── .env.example        ← Environment variable template
├── .env                ← Actual config (not in git)
├── .venv/              ← Python virtual environment (not in git)
├── cookies.txt         ← YouTube cookies (not in git)
├── requirements.txt    ← Python dependencies
├── schema.sql          ← Database table definitions (youtube_channels, youtube_videos)
├── config.py           ← Crawler config (langs, paths, DB env)
├── scraper.py          ← yt-dlp subtitle scraper functions
├── db.py               ← Database write helpers (read-write)
├── main.py             ← Crawler main entry point (read-write)
├── query_db.py         ← Database query tool (read-only)
├── SKILL.md            ← Query skill definition
├── SKILL_SETUP.md      ← This file (setup skill)
└── README.md           ← User-facing documentation
```
