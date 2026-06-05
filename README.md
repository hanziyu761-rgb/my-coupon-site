# 数字人短视频流水线

高阳纺织 AI 内容自动化流水线：下载 → 转写 → 仿写 → 渲染 → 分发。

```
downloads/          原始下载视频
transcripts/        转写稿 / 纠错稿 / 仿写稿
01-download/        第1步：视频下载（f2 / yt-dlp）
02-transcribe/      第2步：转写纠错 + 第3步：仿写
03-remotion/        第4步：字幕动画渲染（Remotion）
04-distribute/      第5步：一键多平台分发
scripts/            pipeline.sh 一键跑全链路
out/                最终产物
```

## 快速开始

### 环境要求

```bash
# Python 依赖
pip install yt-dlp f2 anthropic funasr modelscope

# Node（Remotion 渲染）
node >= 18
cd 03-remotion && npm install

# ffmpeg（提取音频）
# macOS: brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg

# Playwright（分发自动化）
pip install playwright && playwright install chromium
```

### 环境变量

```bash
export ANTHROPIC_API_KEY=sk-ant-xxxx   # Claude 纠错/仿写
export OPENAI_API_KEY=sk-xxxx          # 可选，用 Whisper API 转写
```

## 分步使用

### 第1步：下载对标视频

```bash
python 01-download/download.py --platform youtube --url "URL"
python 01-download/download.py --platform douyin --user "主页URL" --limit 20
```

### 第2步：转写 + 纠错

```bash
# 有 GPU（推荐）
python 02-transcribe/transcribe.py --input downloads/video.mp4 --engine funasr --fix

# 无 GPU
python 02-transcribe/transcribe.py --input downloads/video.mp4 --engine faster-whisper --fix
```

### 第3步：仿写成你的风格

```bash
python 02-transcribe/rewrite.py --input transcripts/video_fixed.txt --duration 60
```
输出文件在 `transcripts/video_fixed_rewrite_60s.txt`，包含逐句时间戳。

### 第4步：渲染字幕动画

1. 把仿写稿内容更新到 `03-remotion/src/Root/sampleScript.ts`（照着 `segments` 格式填）
2. 运行渲染：

```bash
cd 03-remotion
npm install
npm run start   # 浏览器预览（Remotion Studio）
npm run render  # 输出 out/video.mp4（自动探测系统 Chromium）
```

> `npm run render` 会调用 `render.sh`，自动找系统已装的 Chromium 并用 `--chrome-mode=chrome-for-testing`，
> 这样无需联网下载 chrome-headless-shell。已在 4核/无GPU 环境实测渲染成功（63秒视频约2分钟出片）。

**修改文案的最小操作：** 只改 `sampleScript.ts` 里每个 segment 的 `text` 字段，`from` 和 `durationInFrames` 控制出现时间。

### 第5步：一键分发

1. 配置各平台 cookie（首次需扫码登录）：
   ```bash
   python -c "from uploader.douyin_uploader.main import douyin_setup; douyin_setup('04-distribute/cookies/douyin.json', handle=True)"
   ```
2. 修改 `04-distribute/publish.json`
3. 发布：
   ```bash
   python 04-distribute/distribute.py --config 04-distribute/publish.json
   ```

## 算力说明

| 步骤 | 需要 GPU？ | 你的2核2G服务器 |
|------|-----------|----------------|
| 下载 | 否 | ✅ 可以跑 |
| Whisper 转写 | 强烈建议 | ⚠️ CPU 可跑，很慢 |
| Claude 纠错/仿写 | 否（API） | ✅ 可以跑 |
| Remotion 渲染 | 否（CPU） | ✅ 可以跑（慢） |
| IndexTTS2 声音克隆 | ≥6GB 显存 | ❌ 需要 GPU 实例 |
| LatentSync 对口型 | ≥8GB 显存 | ❌ 需要 GPU 实例 |
| 分发 | 否 | ✅ 可以跑 |

> GPU 推荐按需租用：AutoDL / 揽睿 / 恒源云，3090 约1–2元/小时。

## 合规提示

- 2025年9月起 AI 生成内容需标识，本模板已在视频右下角加"AI 生成内容"水印。
- 下载对标视频仅用于研究内容结构，仿写后发布原创内容，禁止搬运原片。
