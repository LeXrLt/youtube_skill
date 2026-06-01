#!/usr/bin/env python3
"""
YouTube 频道字幕抓取 — 入口脚本（读写，写入 PostgreSQL）。

支持两种模式：
1. 直接指定频道（--channel HANDLE_OR_URL）：自动登记/复用 crawl_targets 记录后抓取。
2. 从数据库读取目标（默认 / --target-id）：抓取 crawl_targets 中 source_type='youtube'
   且 enabled=true 的所有目标。

程序状态与进度通过 financial_hub_postgres 的 FinancialHubClient 同步到
crawl_runs / crawl_targets / system_events / component_status；
视频字幕数据写入 youtube_channels / youtube_videos。
"""

import argparse
import os
import sys
import time

import psycopg2
from financial_hub_postgres import FinancialHubClient

import config
import db
import scraper


def get_db_connection():
    """创建并返回 PostgreSQL 数据库连接。"""
    return psycopg2.connect(
        host=config.POSTGRES_HOST,
        port=config.POSTGRES_PORT,
        user=config.POSTGRES_USER,
        password=config.POSTGRES_PASSWORD,
        dbname=config.POSTGRES_DB,
    )


def crawl_target(conn, client: FinancialHubClient, target, max_items: int = 0):
    """对单个 YouTube 目标执行一次完整抓取周期。"""
    print(f"\n{'─' * 50}")
    print(f"目标: [{target.id}] {target.target_name} ({target.target_identifier})")
    print(f"{'─' * 50}")

    channel_url = scraper.normalize_channel_url(target.target_identifier)

    # ── Step 1: 通知开始 ──
    run = client.notify_crawl_start(
        target_id=target.id,
        component_name=config.COMPONENT_NAME,
        metadata={"trigger": "manual", "max_items": max_items},
    )
    print(f"[1/4] crawl_run id={run.id}, status=running")

    start_time = time.time()
    items_found = 0
    items_new = 0
    items_failed = 0

    try:
        # ── Step 2: 获取视频列表 ──
        print("[2/4] 获取频道视频列表 ...")
        videos, channel_id, handle, channel_title = scraper.get_channel_videos(channel_url)
        if not channel_id:
            raise RuntimeError("无法获取频道信息（cookies 可能已过期）")

        db.ensure_channel(conn, channel_id, handle=handle, title=channel_title,
                          channel_url=channel_url)

        if max_items and max_items > 0:
            videos = videos[:max_items]
        items_found = len(videos)

        # 断点续传：跳过已完成的视频
        done = db.get_done_video_ids(conn, channel_id)
        pending = [v for v in videos if v["id"] not in done]
        print(f"[3/4] 共 {items_found} 个视频，已完成 {len(done)}，待下载 {len(pending)}")

        channel_output_dir = os.path.join(config.OUTPUT_DIR, handle or channel_id)

        # ── Step 3: 逐个下载字幕并写库 ──
        for idx, video in enumerate(pending, 1):
            video_id = video["id"]
            title = video["title"]
            print(f"   [{idx}/{len(pending)}] {title} ({video_id})")

            status, sub_path, sub_lang = scraper.download_subtitle_for_video(
                video_id, channel_output_dir
            )

            if status == "rate_limited":
                print("   ✗ 被 YouTube 限流 (HTTP 429)，已停止。进度已保存，可稍后重跑续传。")
                break

            subtitle_text = ""
            error = None
            if status == "success":
                subtitle_text = scraper.srt_to_text(sub_path)
                items_new += 1
                print(f"   ✓ 下载成功 (lang={sub_lang})")
            elif status == "no_subtitle":
                print("   - 无可用字幕")
            elif status == "skipped":
                print("   - 跳过（私密/不可用）")
            elif status.startswith("error"):
                error = status
                items_failed += 1
                print(f"   ✗ {status}")

            db.save_video(
                conn, channel_id, video,
                status=status if not status.startswith("error") else "error",
                subtitle_lang=sub_lang,
                subtitle_format=config.SUBTITLE_FORMAT if status == "success" else None,
                subtitle_path=os.path.abspath(sub_path) if sub_path else None,
                subtitle_text=subtitle_text,
                error=error,
            )

            time.sleep(config.DOWNLOAD_DELAY)

        duration_ms = int((time.time() - start_time) * 1000)

        # ── Step 4: 通知成功 ──
        client.notify_crawl_end(
            run_id=run.id,
            target_id=target.id,
            component_name=config.COMPONENT_NAME,
            success=True,
            items_found=items_found,
            items_new=items_new,
            items_failed=items_failed,
            duration_ms=duration_ms,
        )
        print(f"\n  ✓ 完成: found={items_found}, new={items_new}, "
              f"failed={items_failed}, duration={duration_ms}ms")

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        client.notify_crawl_end(
            run_id=run.id,
            target_id=target.id,
            component_name=config.COMPONENT_NAME,
            success=False,
            items_found=items_found,
            items_new=items_new,
            items_failed=items_failed,
            error_message=str(e),
            duration_ms=duration_ms,
        )
        print(f"\n  ✗ 抓取失败: {e} (duration={duration_ms}ms)", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="YouTube 频道字幕抓取器")
    parser.add_argument(
        "--channel", type=str, default=None,
        help="直接指定频道 handle 或 URL（如 thu4878 或 https://www.youtube.com/@thu4878）",
    )
    parser.add_argument(
        "--target-id", type=int, default=None,
        help="指定 crawl_targets 中的目标 ID",
    )
    parser.add_argument(
        "-n", "--max-items", type=int, default=0,
        help="每个频道最多抓取的视频数（默认 0 = 不限制）",
    )
    args = parser.parse_args()

    print("=" * 60)
    print(" YouTube Channel Subtitle Crawler")
    print("=" * 60)

    conn = get_db_connection()
    client = FinancialHubClient(conn)

    try:
        db.ensure_tables(conn)

        # 确定目标列表
        if args.channel:
            target_id = db.ensure_target(conn, config.SOURCE_TYPE, args.channel)
            target = client.get_crawl_target_by_id(target_id)
            targets = [target]
        elif args.target_id:
            target = client.get_crawl_target_by_id(args.target_id)
            if not target:
                print(f"[ERROR] 未找到 target_id={args.target_id}", file=sys.stderr)
                sys.exit(1)
            targets = [target]
        else:
            targets = client.get_crawl_targets(source_type=config.SOURCE_TYPE, enabled=True)

        if not targets:
            print("[ERROR] 没有可用的 youtube 抓取目标。请用 --channel 指定，"
                  "或在 crawl_targets 中添加 source_type='youtube' 的记录。",
                  file=sys.stderr)
            sys.exit(1)

        for target in targets:
            crawl_target(conn, client, target, max_items=args.max_items)

    finally:
        conn.close()
        print("\nDone.")


if __name__ == "__main__":
    main()
