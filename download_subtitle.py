import yt_dlp


def download_subtitle(url, langs=None):
    """下载指定YouTube视频的简体中文字幕"""
    if langs is None:
        langs = ["zh-Hans", "zh-CN"]
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": langs,
        "subtitlesformat": "srt",
        "outtmpl": "%(title)s.%(ext)s",
        "cookiefile": "cookies.txt",
        "ignore_no_formats_error": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


if __name__ == "__main__":
    video_url = "https://www.youtube.com/watch?v=dRYtB9Qe3Jg"
    download_subtitle(video_url)
