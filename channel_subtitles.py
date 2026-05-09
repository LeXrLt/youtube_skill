"""
下载指定YouTube频道全部视频的简体中文字幕，支持断点续传和增量下载。

用法:
    python channel_subtitles.py <channel_url>

示例:
    python channel_subtitles.py "https://www.youtube.com/@Johnny_vlog"
"""

import json
import os
import re
import sys
import time

import yt_dlp

# 确保 deno 在 PATH 中，供 yt-dlp 使用
DENO_BIN = os.path.expanduser("~/.deno/bin")
if DENO_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = DENO_BIN + os.pathsep + os.environ.get("PATH", "")

# 配置
COOKIES_FILE = "cookies.txt"
SUBTITLE_LANGS = ["zh-Hans", "zh-CN", "en"]
SUBTITLE_FORMAT = "srt"
OUTPUT_DIR = "subtitles"
PROGRESS_FILE = "download_progress.json"


def load_progress(channel_id):
    """加载下载进度记录"""
    if not os.path.exists(PROGRESS_FILE):
        return {}
    with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
        all_progress = json.load(f)
    return all_progress.get(channel_id, {})


def save_progress(channel_id, progress):
    """保存下载进度记录"""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            all_progress = json.load(f)
    else:
        all_progress = {}
    all_progress[channel_id] = progress
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)


def extract_channel_handle(channel_url):
    """从频道URL中提取handle名称，如 https://www.youtube.com/@laogao -> laogao"""
    match = re.search(r"/@([^/]+)", channel_url)
    if match:
        return match.group(1)
    return None


def get_channel_videos(channel_url):
    """获取频道所有视频的基本信息，返回 (videos, channel_id, channel_handle)"""
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "cookiefile": COOKIES_FILE,
        "ignore_no_formats_error": True,
    }

    # 从URL提取频道handle名称
    channel_handle = extract_channel_handle(channel_url)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # 获取频道的 /videos 页面
        if not channel_url.endswith("/videos"):
            videos_url = channel_url.rstrip("/") + "/videos"
        else:
            videos_url = channel_url

        print(f"[INFO] 正在获取频道视频列表: {videos_url}")
        info = ydl.extract_info(videos_url, download=False)

        if info is None:
            print("[ERROR] 无法获取频道信息")
            return [], None, None

        channel_id = info.get("channel_id") or info.get("id", "unknown")
        # 如果URL中没提取到handle，用channel_id作为fallback
        if not channel_handle:
            channel_handle = channel_id
        entries = info.get("entries", [])

        videos = []
        for entry in entries:
            if entry is None:
                continue
            video_id = entry.get("id")
            title = entry.get("title", "unknown")
            if video_id:
                videos.append({"id": video_id, "title": title})

        print(f"[INFO] 频道: {channel_handle} ({channel_id}), 共找到 {len(videos)} 个视频")
        return videos, channel_id, channel_handle


def download_subtitle_for_video(video_id, output_dir):
    """下载单个视频的字幕，返回状态: success / no_subtitle / rate_limited / skipped / error:..."""
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": SUBTITLE_LANGS,
        "subtitlesformat": SUBTITLE_FORMAT,
        "outtmpl": os.path.join(output_dir, "%(id)s_%(title)s.%(ext)s"),
        "cookiefile": COOKIES_FILE,
        "ignore_no_formats_error": True,
        "quiet": True,
        "no_warnings": True,
    }

    # 记录下载前目录中的文件
    before = set(os.listdir(output_dir)) if os.path.isdir(output_dir) else set()

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            return "rate_limited"
        if "Private video" in error_msg or "Video unavailable" in error_msg:
            return "skipped"
        return f"error: {error_msg}"

    # 检查是否有新字幕文件生成
    after = set(os.listdir(output_dir)) if os.path.isdir(output_dir) else set()
    new_files = [f for f in (after - before) if f.endswith(f".{SUBTITLE_FORMAT}")]

    if new_files:
        return "success"
    else:
        return "no_subtitle"


def run(channel_url):
    """主流程: 下载频道全部视频字幕，支持断点续传"""
    # 1. 获取频道视频列表
    videos, channel_id, channel_handle = get_channel_videos(channel_url)
    if not videos:
        print("[ERROR] 未找到任何视频，退出")
        return

    # 2. 创建输出目录 (使用频道handle名称)
    channel_output_dir = os.path.join(OUTPUT_DIR, channel_handle)
    os.makedirs(channel_output_dir, exist_ok=True)

    # 3. 加载已有进度
    progress = load_progress(channel_id)
    downloaded = progress.get("downloaded", {})
    total = len(videos)
    already_done = sum(1 for v in videos if v["id"] in downloaded)

    print(f"[INFO] 总视频数: {total}, 已完成: {already_done}, 待下载: {total - already_done}")

    # 4. 逐个下载字幕
    for idx, video in enumerate(videos, 1):
        video_id = video["id"]
        title = video["title"]

        if video_id in downloaded:
            continue

        print(f"[{idx}/{total}] 正在下载字幕: {title} ({video_id})")
        result = download_subtitle_for_video(video_id, channel_output_dir)

        if result == "rate_limited":
            print(f"  ✗ 请求过于频繁 (HTTP 429)，已自动停止。")
            print(f"\n[中断] 已被YouTube限流，请稍后再试。已完成的进度已保存，下次运行将自动续传。")
            return

        # 记录结果
        downloaded[video_id] = {
            "title": title,
            "status": result,
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        progress["downloaded"] = downloaded
        save_progress(channel_id, progress)

        if result == "success":
            print(f"  ✓ 下载成功")
        elif result == "no_subtitle":
            print(f"  - 无可用字幕")
        elif result == "skipped":
            print(f"  - 跳过 (私密/不可用)")
        else:
            print(f"  ✗ {result}")

        # 简单限速，避免被封
        time.sleep(1)

    # 5. 汇总
    success_count = sum(1 for v in downloaded.values() if v["status"] == "success")
    no_sub_count = sum(1 for v in downloaded.values() if v["status"] == "no_subtitle")
    skip_count = sum(1 for v in downloaded.values() if v["status"] == "skipped")
    error_count = sum(1 for v in downloaded.values() if v["status"].startswith("error"))
    print(f"\n[完成] 成功: {success_count}, 无字幕: {no_sub_count}, 跳过: {skip_count}, 失败: {error_count}")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(f"用法: python {sys.argv[0]} <channel_handle_or_url>")
        print(f'示例: python {sys.argv[0]} thu4878')
        print(f'      python {sys.argv[0]} "https://www.youtube.com/@Johnny_vlog"')
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    arg = sys.argv[1]
    # 支持直接传入频道handle，自动构造URL
    if arg.startswith("http"):
        channel_url = arg
    else:
        handle = arg.lstrip("@")
        channel_url = f"https://www.youtube.com/@{handle}"

    run(channel_url)
