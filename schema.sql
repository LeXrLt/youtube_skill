-- YouTube 字幕爬虫数据表
-- 设计原则（参照 sec_skill / substack_skill）：
-- - 每个数据源拥有自己的表
-- - 保留 raw_data JSONB 原始响应
-- - status 字段记录每个视频的抓取状态，支持断点续传与去重

-- YouTube 频道
CREATE TABLE IF NOT EXISTS youtube_channels (
    id              SERIAL PRIMARY KEY,
    channel_id      VARCHAR(64)     NOT NULL UNIQUE,   -- YouTube 频道 ID (UC...)
    handle          VARCHAR(255)    NOT NULL DEFAULT '', -- 频道 handle (@xxx 去掉 @)
    title           VARCHAR(500)    NOT NULL DEFAULT '',
    channel_url     VARCHAR(1000)   NOT NULL DEFAULT '',
    notes           TEXT,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW()
);

-- YouTube 视频及其字幕
CREATE TABLE IF NOT EXISTS youtube_videos (
    id              SERIAL PRIMARY KEY,
    channel_id      VARCHAR(64)     NOT NULL REFERENCES youtube_channels(channel_id),
    video_id        VARCHAR(32)     NOT NULL,          -- YouTube 视频 ID
    title           VARCHAR(1000)   NOT NULL DEFAULT '',
    video_url       VARCHAR(1000)   NOT NULL DEFAULT '',
    subtitle_lang   VARCHAR(20)     DEFAULT NULL,      -- 实际下载到的字幕语言
    subtitle_format VARCHAR(20)     DEFAULT NULL,
    subtitle_path   VARCHAR(1000)   DEFAULT NULL,      -- 本地字幕文件路径
    subtitle_text   TEXT            DEFAULT '',        -- 字幕纯文本内容
    status          VARCHAR(50)     NOT NULL DEFAULT 'pending', -- success / no_subtitle / skipped / error / pending
    error           TEXT,
    raw_data        JSONB           NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_youtube_videos_channel_video UNIQUE (channel_id, video_id)
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_youtube_videos_channel
    ON youtube_videos (channel_id);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_video
    ON youtube_videos (video_id);
CREATE INDEX IF NOT EXISTS idx_youtube_videos_status
    ON youtube_videos (status);
CREATE INDEX IF NOT EXISTS idx_youtube_channels_handle
    ON youtube_channels (handle);
