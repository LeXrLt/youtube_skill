"""
[已废弃] 旧的 JSON 进度版字幕下载入口。

字幕抓取逻辑已迁移到数据库版本：
    - scraper.py  : yt-dlp 抓取函数
    - main.py     : 爬虫入口（写入 PostgreSQL，状态/进度通过 financial_hub_postgres 同步）

本文件仅作向后兼容：把旧的 `python channel_subtitles.py <handle_or_url>` 调用
转发到新的 `main.py --channel <handle_or_url>`。

新用法:
    python main.py --channel thu4878
    python main.py --channel "https://www.youtube.com/@laogao"
"""

import sys

from main import main as crawler_main


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(f"用法: python {sys.argv[0]} <channel_handle_or_url>")
        print("注意: 本入口已废弃，等价于 python main.py --channel <channel_handle_or_url>")
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    # 将旧的位置参数转换为 main.py 的 --channel 参数
    arg = sys.argv[1]
    sys.argv = [sys.argv[0], "--channel", arg]
    crawler_main()
