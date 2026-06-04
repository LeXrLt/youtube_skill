"""YouTube 字幕爬虫配置"""

import os

from dotenv import load_dotenv

load_dotenv()

# yt-dlp / cookies 配置
COOKIES_FILE = os.path.join(os.path.dirname(__file__), "cookies.txt")

# 字幕语言优先级：简体中文 -> 英文 -> 默认
SUBTITLE_LANGS = ["zh-Hans", "zh-CN", "en"]
SUBTITLE_FORMAT = "srt"

# 字幕本地输出目录
# 优先使用环境变量 CRAWLER_OUTPUT_DIR（由 financial_hub 在下载根目录后拼接 source_type 注入），
# 未设置时回退到项目内 subtitles 目录。
OUTPUT_DIR = os.getenv("CRAWLER_OUTPUT_DIR") or os.path.join(
    os.path.dirname(__file__), "subtitles"
)

# 每个视频下载后的限速（秒），避免被 YouTube 限流
DOWNLOAD_DELAY = 1

# PostgreSQL 数据库配置（financial_hub_postgres 插件，从 .env 读取）
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_USER = os.getenv("POSTGRES_USER", "hub_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "hub_password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "financial_hub")

# 爬虫组件名称（用于 financial_hub_postgres 生命周期上报）
COMPONENT_NAME = "youtube_crawler"

# crawl_targets 中本数据源的类型标识
SOURCE_TYPE = "youtube"
