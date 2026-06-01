"""
YouTube database query tool (read-only).

Provides CLI access to query youtube_channels and youtube_videos tables.
Strictly SELECT-only — no INSERT, UPDATE, or DELETE operations.

Usage:
    python query_db.py channels
    python query_db.py videos [--channel HANDLE_OR_ID] [--search KEYWORD]
                              [--status STATUS] [--limit N] [--offset N]
                              [--id ID] [--full]
    python query_db.py stats [--channel HANDLE_OR_ID]
"""

import os
import json
import argparse

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv


# Load environment variables from .env (same as crawler)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


def get_db_connection():
    """Create a read-only database connection using .env config (readonly user)."""
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        user=os.getenv("POSTGRES_READONLY_USER", "hub_readonly"),
        password=os.getenv("POSTGRES_READONLY_PASSWORD", "hub_password"),
        dbname=os.getenv("POSTGRES_DB", "financial_hub"),
    )
    conn.set_session(readonly=True, autocommit=True)
    return conn


# ---------------------------------------------------------------------------
# Output formatting — stable structure for AI Agent consumption
# ---------------------------------------------------------------------------

ITEM_SEPARATOR = "\n" + "=" * 60 + "\n"


def format_channel(row: dict) -> str:
    """Format a single channel record."""
    lines = [
        f"频道: {row.get('title') or '(未知)'}",
        f"Handle: {row.get('handle') or ''}",
        f"频道ID: {row.get('channel_id') or ''}",
        f"主页: {row.get('channel_url') or ''}",
        f"视频数: {row.get('video_count', 0)}",
        f"已抓字幕: {row.get('with_subtitle', 0)}",
        f"更新时间: {row.get('updated_at', '')}",
    ]
    return "\n".join(lines)


def format_video(row: dict, full: bool = False) -> str:
    """Format a single video record in stable output structure."""
    lines = [
        f"ID: {row.get('id')}",
        f"标题: {row.get('title') or '(无标题)'}",
        f"来源: youtube",
        f"频道: {row.get('channel_title') or row.get('channel_id') or ''}",
        f"视频ID: {row.get('video_id') or ''}",
        f"原始链接: {row.get('video_url') or ''}",
        f"字幕语言: {row.get('subtitle_lang') or ''}",
        f"状态: {row.get('status') or ''}",
    ]

    if row.get("subtitle_path"):
        lines.append(f"本地字幕: {row['subtitle_path']}")
    if row.get("error"):
        lines.append(f"错误: {row['error']}")

    text = row.get("subtitle_text") or ""
    if full:
        lines.append("")
        lines.append("--- 字幕全文 ---")
        lines.append(text if text else "(无字幕)")
    else:
        preview = text[:200].replace("\n", " ") if text else "(无字幕)"
        if len(text) > 200:
            preview += "..."
        lines.append(f"字幕预览: {preview}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def _channel_condition(value: str):
    """根据传入值（handle 或 channel_id）构造频道过滤条件。"""
    return "(c.handle = %s OR c.channel_id = %s OR v.channel_id = %s)", [value, value, value]


def cmd_channels(conn, args):
    """List all channels with video counts."""
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT c.*,
                   COUNT(v.id) AS video_count,
                   COUNT(v.id) FILTER (WHERE v.status = 'success') AS with_subtitle
            FROM youtube_channels c
            LEFT JOIN youtube_videos v ON v.channel_id = c.channel_id
            GROUP BY c.id
            ORDER BY video_count DESC
            """
        )
        rows = cur.fetchall()

    if not rows:
        print("没有找到任何频道。")
        return

    print(f"共 {len(rows)} 个频道:\n")
    print(ITEM_SEPARATOR.join(format_channel(r) for r in rows))


def cmd_videos(conn, args):
    """Query videos with optional filters."""
    conditions = []
    params = []

    if args.channel:
        cond, p = _channel_condition(args.channel)
        conditions.append(cond)
        params.extend(p)

    if args.status:
        conditions.append("v.status = %s")
        params.append(args.status)

    if args.search:
        conditions.append("(v.title ILIKE %s OR v.subtitle_text ILIKE %s)")
        pattern = f"%{args.search}%"
        params.extend([pattern, pattern])

    if args.id:
        conditions.append("v.id = %s")
        params.append(args.id)

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    limit = min(args.limit, 500)
    offset = args.offset

    sql = f"""
        SELECT v.*, c.title AS channel_title
        FROM youtube_videos v
        LEFT JOIN youtube_channels c ON c.channel_id = v.channel_id
        {where}
        ORDER BY v.created_at DESC
        LIMIT %s OFFSET %s
    """
    query_params = params + [limit, offset]

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(sql, query_params)
        rows = cur.fetchall()

    if not rows:
        print("没有找到匹配的视频。")
        return

    count_sql = f"""
        SELECT COUNT(*)
        FROM youtube_videos v
        LEFT JOIN youtube_channels c ON c.channel_id = v.channel_id
        {where}
    """
    with conn.cursor() as cur:
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

    print(f"查询结果: {len(rows)} 条 (共 {total} 条匹配, offset={offset}, limit={limit})\n")
    print(ITEM_SEPARATOR.join(format_video(r, full=args.full) for r in rows))


def cmd_stats(conn, args):
    """Show statistics overview."""
    where = ""
    params = []
    if args.channel:
        where = """
            WHERE v.channel_id IN (
                SELECT channel_id FROM youtube_channels
                WHERE handle = %s OR channel_id = %s
            )
        """
        params = [args.channel, args.channel]

    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM youtube_channels")
        channel_count = cur.fetchone()["cnt"]

        cur.execute(
            f"""
            SELECT v.status, COUNT(*) AS cnt
            FROM youtube_videos v
            {where}
            GROUP BY v.status
            ORDER BY cnt DESC
            """,
            params,
        )
        status_rows = cur.fetchall()

        cur.execute(f"SELECT COUNT(*) AS cnt FROM youtube_videos v {where}", params)
        total_videos = cur.fetchone()["cnt"]

    header = "YouTube 统计概览"
    if args.channel:
        header += f" (频道: {args.channel})"

    lines = [
        header,
        f"频道总数: {channel_count}",
        f"视频总数: {total_videos}",
        "",
        "按状态统计:",
    ]
    for r in status_rows:
        lines.append(f"  {r['status'] or '(未知)'}: {r['cnt']} 条")

    print("\n".join(lines))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="YouTube 数据库只读查询工具")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("channels", help="列出所有已抓取的频道")

    p_videos = subparsers.add_parser("videos", help="查询视频及字幕")
    p_videos.add_argument("--channel", type=str, default=None,
                          help="按频道 handle 或 channel_id 过滤")
    p_videos.add_argument("--search", type=str, default=None,
                          help="按关键词搜索标题和字幕全文")
    p_videos.add_argument("--status", type=str, default=None,
                          help="按状态过滤 (success / no_subtitle / skipped / error)")
    p_videos.add_argument("--limit", type=int, default=20, help="返回条数上限 (默认 20, 最大 500)")
    p_videos.add_argument("--offset", type=int, default=0, help="跳过前 N 条 (分页用)")
    p_videos.add_argument("--id", type=int, default=None, help="按数据库 ID 精确查询单条")
    p_videos.add_argument("--full", action="store_true", help="显示完整字幕全文 (默认只显示预览)")

    p_stats = subparsers.add_parser("stats", help="查看统计信息")
    p_stats.add_argument("--channel", type=str, default=None, help="按频道过滤统计")

    args = parser.parse_args()

    conn = get_db_connection()
    try:
        if args.command == "channels":
            cmd_channels(conn, args)
        elif args.command == "videos":
            cmd_videos(conn, args)
        elif args.command == "stats":
            cmd_stats(conn, args)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
