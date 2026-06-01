"""YouTube 字幕抓取函数（基于 yt-dlp，无数据库依赖）"""

import os
import re

import yt_dlp

import config

# 确保 deno 在 PATH 中，供 yt-dlp 使用
DENO_BIN = os.path.expanduser("~/.deno/bin")
if DENO_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = DENO_BIN + os.pathsep + os.environ.get("PATH", "")


def extract_channel_handle(channel_url: str) -> str | None:
    """从频道 URL 中提取 handle，如 https://www.youtube.com/@laogao -> laogao"""
    match = re.search(r"/@([^/]+)", channel_url)
    if match:
        return match.group(1)
    return None


def normalize_channel_url(arg: str) -> str:
    """支持直接传入 handle 或完整 URL，统一返回频道 URL。"""
    if arg.startswith("http"):
        return arg
    handle = arg.lstrip("@")
    return f"https://www.youtube.com/@{handle}"


def get_channel_videos(channel_url: str):
    """
    获取频道所有视频的基本信息。
    返回 (videos, channel_id, channel_handle, channel_title)。
    """
    ydl_opts = {
        "quiet": True,
        "extract_flat": True,
        "cookiefile": config.COOKIES_FILE,
        "ignore_no_formats_error": True,
    }

    channel_handle = extract_channel_handle(channel_url)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        videos_url = channel_url if channel_url.endswith("/videos") else channel_url.rstrip("/") + "/videos"

        print(f"[INFO] 正在获取频道视频列表: {videos_url}")
        info = ydl.extract_info(videos_url, download=False)

        if info is None:
            print("[ERROR] 无法获取频道信息")
            return [], None, None, ""

        channel_id = info.get("channel_id") or info.get("id", "unknown")
        channel_title = info.get("channel") or info.get("title", "") or ""
        if not channel_handle:
            channel_handle = info.get("uploader_id", "").lstrip("@") or channel_id

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
        return videos, channel_id, channel_handle, channel_title


def srt_to_text(srt_path: str) -> str:
    """将 SRT 字幕文件转换为纯文本（去掉序号和时间轴）。"""
    if not srt_path or not os.path.exists(srt_path):
        return ""
    lines = []
    with open(srt_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = raw.strip()
            if not line:
                continue
            if line.isdigit():
                continue
            if "-->" in line:
                continue
            # 去除内嵌的 HTML/格式标签
            line = re.sub(r"<[^>]+>", "", line)
            lines.append(line)
    # 去重连续重复行（自动字幕常见）
    deduped = []
    for line in lines:
        if not deduped or deduped[-1] != line:
            deduped.append(line)
    return "\n".join(deduped)


def download_subtitle_for_video(video_id: str, output_dir: str):
    """
    下载单个视频的字幕。
    返回 (status, subtitle_path, subtitle_lang)。
    status: success / no_subtitle / rate_limited / skipped / error:<msg>
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": config.SUBTITLE_LANGS,
        "subtitlesformat": config.SUBTITLE_FORMAT,
        "outtmpl": os.path.join(output_dir, "%(id)s_%(title)s.%(ext)s"),
        "cookiefile": config.COOKIES_FILE,
        "ignore_no_formats_error": True,
        "quiet": True,
        "no_warnings": True,
    }

    os.makedirs(output_dir, exist_ok=True)
    before = set(os.listdir(output_dir))

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as e:
        error_msg = str(e)
        if "429" in error_msg or "Too Many Requests" in error_msg:
            return "rate_limited", None, None
        if "Private video" in error_msg or "Video unavailable" in error_msg:
            return "skipped", None, None
        return f"error: {error_msg}", None, None

    after = set(os.listdir(output_dir))
    new_files = [f for f in (after - before) if f.endswith(f".{config.SUBTITLE_FORMAT}")]

    if not new_files:
        return "no_subtitle", None, None

    # 按语言优先级挑选字幕
    chosen = new_files[0]
    chosen_lang = None
    for lang in config.SUBTITLE_LANGS:
        for f in new_files:
            if f".{lang}." in f:
                chosen = f
                chosen_lang = lang
                break
        if chosen_lang:
            break

    return "success", os.path.join(output_dir, chosen), chosen_lang
