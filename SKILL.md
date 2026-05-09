---
name: youtube-subtitle-downloader
description: Download subtitles for all videos from a YouTube channel. Supports Chinese, English and auto-generated subtitles with resume capability.
metadata:
  {
    "openclaw":
      {
        "emoji": "📺",
        "requires": { "bins": ["python3"], "os": ["linux", "darwin"] },
      },
  }
---

# YouTube Subtitle Downloader

## What it does

Downloads subtitles for all videos from a specified YouTube channel. Supports:

- Simplified Chinese → English → default language fallback
- Breakpoint resume (interrupted downloads can be continued)
- Incremental updates (only downloads new videos)
- Rate limiting detection (auto-stops on HTTP 429)

## Inputs needed

- **Channel handle**: The YouTube channel handle (e.g. `thu4878`, `laogao`, `3blue1brown`). Can also be a full URL like `https://www.youtube.com/@thu4878`.
- The project lives at `{baseDir}` and requires `cookies.txt` in that directory for YouTube authentication.

## Workflow

1. Parse the user's request to extract the YouTube channel handle or URL.
   - If the user says something like "下载 thu4878 频道的字幕", extract `thu4878`.
   - If the user provides a full URL like `https://www.youtube.com/@thu4878`, use it directly.
   - Strip any leading `@` from the handle.

2. Run the download script:

   ```bash
   cd {baseDir} && .venv/bin/python channel_subtitles.py <channel_handle_or_url>
   ```

   This command may run for a long time depending on the number of videos. Run it non-blocking so the user can monitor progress.

3. Report the results to the user. The script will output:
   - Total videos found
   - Per-video download status (success / no subtitle / skipped / error)
   - Final summary with counts

## Output format

Relay the script's terminal output to the user. After completion, summarize:

- Total videos processed
- Subtitles downloaded successfully
- Videos with no available subtitles
- Any errors encountered

Subtitles are saved to `{baseDir}/subtitles/<channel_handle>/` in SRT format.

## Guardrails

- Never modify or delete existing subtitle files.
- Never modify `cookies.txt`.
- If the script reports HTTP 429 (rate limited), tell the user to wait 10-30 minutes before retrying.
- If the script reports "Sign in to confirm you're not a bot", tell the user their `cookies.txt` may be expired and needs to be refreshed.
- Do not attempt to download videos or audio — this skill is for subtitles only.

## Failure handling

- If `cookies.txt` is missing, tell the user to export YouTube cookies using a browser extension (e.g. Cookie-Editor) in Netscape format and save to `{baseDir}/cookies.txt`.
- If `.venv` does not exist, run: `cd {baseDir} && python3 -m venv .venv && .venv/bin/pip install "yt-dlp @ git+https://github.com/yt-dlp/yt-dlp.git"`
- If rate limited (429), the script auto-stops and saves progress. The user can simply re-run the same command later to resume.

## Examples

User: "请下载YouTube thu4878 频道下的所有字幕"
Action: `cd {baseDir} && .venv/bin/python channel_subtitles.py thu4878`

User: "下载 https://www.youtube.com/@laogao 的字幕"
Action: `cd {baseDir} && .venv/bin/python channel_subtitles.py "https://www.youtube.com/@laogao"`

User: "Download subtitles from 3blue1brown channel"
Action: `cd {baseDir} && .venv/bin/python channel_subtitles.py 3blue1brown`
