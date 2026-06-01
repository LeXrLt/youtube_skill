"""YouTube 字幕爬虫数据库操作模块（读写）"""

import json
import os

SCHEMA_FILE = os.path.join(os.path.dirname(__file__), "schema.sql")


def ensure_tables(conn):
    """检测并创建数据表（基于 schema.sql）。"""
    with open(SCHEMA_FILE, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    conn.commit()
    print("[DB] 数据表检查/创建完成")


def ensure_channel(conn, channel_id: str, handle: str = "", title: str = "",
                   channel_url: str = ""):
    """插入或更新频道记录。"""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO youtube_channels (channel_id, handle, title, channel_url)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (channel_id) DO UPDATE SET
                handle = COALESCE(NULLIF(EXCLUDED.handle, ''), youtube_channels.handle),
                title = COALESCE(NULLIF(EXCLUDED.title, ''), youtube_channels.title),
                channel_url = COALESCE(NULLIF(EXCLUDED.channel_url, ''), youtube_channels.channel_url),
                updated_at = NOW()
            """,
            (channel_id, handle, title, channel_url),
        )
    conn.commit()


def get_done_video_ids(conn, channel_id: str) -> set[str]:
    """返回已处理完成（非 pending/error）的 video_id 集合，用于断点续传。"""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT video_id FROM youtube_videos
            WHERE channel_id = %s AND status IN ('success', 'no_subtitle', 'skipped')
            """,
            (channel_id,),
        )
        return {row[0] for row in cur.fetchall()}


def save_video(conn, channel_id: str, video: dict, status: str,
               subtitle_lang: str | None = None, subtitle_format: str | None = None,
               subtitle_path: str | None = None, subtitle_text: str = "",
               error: str | None = None) -> bool:
    """
    插入或更新一条视频/字幕记录。
    返回是否为新插入（True 表示首次插入，False 表示已存在被更新）。
    """
    video_id = video.get("id", "")
    if not video_id:
        return False

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO youtube_videos
                (channel_id, video_id, title, video_url, subtitle_lang,
                 subtitle_format, subtitle_path, subtitle_text, status, error, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (channel_id, video_id) DO UPDATE SET
                title = EXCLUDED.title,
                video_url = EXCLUDED.video_url,
                subtitle_lang = EXCLUDED.subtitle_lang,
                subtitle_format = EXCLUDED.subtitle_format,
                subtitle_path = EXCLUDED.subtitle_path,
                subtitle_text = EXCLUDED.subtitle_text,
                status = EXCLUDED.status,
                error = EXCLUDED.error,
                raw_data = EXCLUDED.raw_data,
                updated_at = NOW()
            RETURNING (xmax = 0) AS inserted
            """,
            (
                channel_id,
                video_id,
                video.get("title", ""),
                f"https://www.youtube.com/watch?v={video_id}",
                subtitle_lang,
                subtitle_format,
                subtitle_path,
                subtitle_text,
                status,
                error,
                json.dumps(video, ensure_ascii=False, default=str),
            ),
        )
        inserted = cur.fetchone()[0]
    conn.commit()
    return bool(inserted)


def ensure_target(conn, source_type: str, identifier: str, name: str = "") -> int:
    """
    查找 crawl_targets 中匹配的目标；若不存在则创建。返回 target_id。
    用于直接通过频道参数运行时，仍能进行状态/进度上报。
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM crawl_targets
            WHERE source_type = %s AND target_identifier = %s
            ORDER BY id ASC LIMIT 1
            """,
            (source_type, identifier),
        )
        row = cur.fetchone()
        if row:
            return row[0]

        cur.execute(
            """
            INSERT INTO crawl_targets (source_type, target_name, target_identifier, enabled)
            VALUES (%s, %s, %s, true)
            RETURNING id
            """,
            (source_type, name or identifier, identifier),
        )
        target_id = cur.fetchone()[0]
    conn.commit()
    return target_id
