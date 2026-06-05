# 数字人短视频智能体

高阳纺织 AI 内容自动化流水线，一条命令跑完六步：
**下载 → 转写 → 仿写 → 声音克隆 → 字幕动画/对口型 → 一键分发**

```
agent.py               🤖 智能体编排器：一条命令跑完整条流水线
config.example.yaml    配置（身份/各步开关），复制为 config.yaml 使用
requirements.txt       Python 依赖

01-download/           第1步：视频下载（yt-dlp / f2）
02-transcribe/         第2步：Whisper 转写 + Claude 纠错
03-rewrite/            第3步：仿写成你的风格（内置高阳纺织 prompt）
04-voice-clone/        第4步：IndexTTS2 声音克隆（需 GPU）
05-render-remotion/    第5步：Remotion 字幕动画 + LatentSync 对口型（需 GPU）
06-distribute/         第6步：social-auto-upload 一键分发多平台

downloads/  transcripts/  out/   过程文件与成品
```

## 🤖 用智能体一键跑（推荐）

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml   # 改成你的配置（下载源、各步开关）
export ANTHROPIC_API_KEY=sk-ant-xxx  # 纠错/仿写/字幕排版

python agent.py                       # 跑全流程
python agent.py --url "<视频URL>"     # 临时指定下载源
python agent.py --from 3              # 从仿写开始（前面已有产物时）
python agent.py --only 5              # 只渲染
python agent.py --script my.txt       # 跳过前3步，直接用现成文案出片
```

无 GPU 时把 `config.yaml` 里 `voice.enabled` / `lipsync.enabled` 留 `false`，
智能体会自动跳过这两步，仍产出「字幕动画」成品视频（已实测可在 4核/无GPU 跑通）。

## 分步手动使用

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
# 有 GPU（推荐，中文最佳）
python 02-transcribe/transcribe.py --input downloads/video.mp4 --engine funasr --fix
# 无 GPU
python 02-transcribe/transcribe.py --input downloads/video.mp4 --engine faster-whisper --fix
```

### 第3步：仿写成你的风格

```bash
python 03-rewrite/rewrite.py --input transcripts/video_fixed.txt --duration 60
```
输出 `transcripts/video_fixed_rewrite_60s.txt`，含逐句时间戳。

### 第4步：声音克隆（IndexTTS2，需 GPU）

```bash
cd 04-voice-clone
python tts_indextts2.py --setup                      # 装环境 + 从魔搭下载模型
python tts_indextts2.py --ref my_voice.wav \         # 你的参考录音 3-10秒
    --text-file ../transcripts/xxx_rewrite_60s.txt \
    --out ../out/voice.wav
```

### 第5步：字幕动画渲染（Remotion）+ 对口型（LatentSync）

```bash
cd 05-render-remotion
npm install
# 仿写稿 → 字幕时间轴 props.json（带配音则自动对齐时长 + 挂音轨）
python build_props.py --input ../transcripts/xxx_rewrite_60s.txt \
    --audio ../out/voice.wav --out props.json
# 渲染（自动探测系统 Chromium，用 chrome-for-testing 模式免下载）
bash render.sh out/video.mp4 props.json

# 可选：有真人口播底片时做对口型（需 GPU）
python latentsync.py --setup
python latentsync.py --video face.mp4 --audio ../out/voice.wav --out ../out/lipsync.mp4
```

> 渲染已在 4核/无GPU 环境实测跑通（约2分钟出片）。无 `ANTHROPIC_API_KEY` 时
> `build_props.py` 会用本地兜底切分；加 key 后字幕断句和关键词高亮更精准。

### 第6步：一键分发

1. 配置各平台 cookie（首次扫码登录）：
   ```bash
   python -c "from uploader.douyin_uploader.main import douyin_setup; douyin_setup('06-distribute/cookies/douyin.json', handle=True)"
   ```
2. 修改 `06-distribute/publish.json` 后发布：
   ```bash
   python 06-distribute/distribute.py --config 06-distribute/publish.json
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
