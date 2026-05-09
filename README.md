# 📺 YouTube Subtitle Downloader

一个 [OpenClaw](https://openclaw.ai/) skill，帮你批量下载 YouTube 频道的所有视频字幕。

只需用自然语言告诉 OpenClaw 你想下载哪个频道的字幕，剩下的它会帮你搞定。

## 功能特点

- 下载指定频道全部视频的字幕（简体中文 → 英文 → 默认语言）
- 支持断点续传，中断后下次自动从上次的位置继续
- 自动检测 YouTube 限流，触发后保存进度并提示稍后重试
- 字幕按频道名分文件夹存放，格式为 SRT

---

## 安装

打开 OpenClaw，直接对它说：

> 请帮我安装这个 skill：https://github.com/LeXrLt/youtube_skill.git

OpenClaw 会自动完成以下操作：
1. 克隆仓库到本地
2. 创建 Python 虚拟环境
3. 安装所需依赖（yt-dlp）

### 准备 Cookies（必需）

由于 YouTube 的反爬机制，下载字幕需要提供你的登录 cookies。

对 OpenClaw 说：

> 我需要配置 YouTube cookies

它会引导你完成以下步骤：
1. 在 Chrome 浏览器中安装 [Cookie-Editor](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm) 扩展
2. 打开 YouTube 并确保你已登录
3. 点击 Cookie-Editor 图标，点击「Export」→ 选择「Netscape」格式
4. 把导出的内容发给 OpenClaw，它会帮你保存为 `cookies.txt`

> 💡 如果后续遇到"Sign in to confirm you're not a bot"的报错，说明 cookies 过期了，重新导出一次即可。

---

## 使用

安装完成后，你可以随时用自然语言下载字幕：

### 示例对话

| 你说 | 效果 |
|------|------|
| "请下载 YouTube thu4878 频道下的所有字幕" | 下载 @thu4878 频道全部视频字幕 |
| "帮我下载 laogao 的 YouTube 字幕" | 下载 @laogao 频道全部视频字幕 |
| "Download subtitles from 3blue1brown" | 下载 @3blue1brown 频道全部视频字幕 |

### 下载过程中

- OpenClaw 会实时显示每个视频的下载状态
- 如果遇到限流（HTTP 429），会自动停止并告诉你稍后再试
- 下次再说同样的话，会自动跳过已下载的视频，从中断处继续

### 字幕存放位置

下载好的字幕保存在项目目录下：

```
subtitles/
  └── <频道名>/
      ├── videoID1_视频标题.zh-Hans.srt
      ├── videoID2_视频标题.en.srt
      └── ...
```

---

## 常见问题

**Q: 提示"cookies 过期"怎么办？**

对 OpenClaw 说："我的 YouTube cookies 过期了，帮我更新"，然后按提示重新导出即可。

**Q: 下载到一半被限流了怎么办？**

等 10~30 分钟后，再说一次"继续下载 xxx 频道的字幕"，会自动从上次中断的地方继续。

**Q: 支持哪些语言的字幕？**

优先下载简体中文字幕，没有则下载英文字幕，再没有则下载视频的默认字幕。如果视频完全没有字幕，会标记为"无可用字幕"并跳过。

**Q: 支持哪些操作系统？**

支持 Linux 和 macOS。

---

## 项目地址

https://github.com/LeXrLt/youtube_skill.git
