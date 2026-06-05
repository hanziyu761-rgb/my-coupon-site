#!/usr/bin/env bash
# 一键跑完整条流水线
# 用法: ./scripts/pipeline.sh <视频URL或本地mp4> <目标秒数>
# 示例: ./scripts/pipeline.sh "https://youtube.com/watch?v=xxx" 60

set -e

VIDEO_INPUT="$1"
DURATION="${2:-60}"
OUT_DIR="$(dirname "$0")/../out"
mkdir -p "$OUT_DIR"

echo "========================================="
echo " 数字人短视频流水线"
echo " 输入: $VIDEO_INPUT"
echo " 目标时长: ${DURATION}s"
echo "========================================="

# ─ 第1步：下载 ──────────────────────────────
if [[ "$VIDEO_INPUT" == http* ]]; then
  echo ""
  echo "[1/5] 下载视频..."
  python 01-download/download.py --platform youtube --url "$VIDEO_INPUT" --output downloads/
  VIDEO_FILE=$(ls downloads/*.mp4 | tail -1)
else
  VIDEO_FILE="$VIDEO_INPUT"
fi
echo "    视频文件: $VIDEO_FILE"

# ─ 第2步：转写 + 纠错 ────────────────────────
echo ""
echo "[2/5] 转写 + 纠错..."
python 02-transcribe/transcribe.py \
  --input "$VIDEO_FILE" \
  --engine auto \
  --fix
TRANSCRIPT=$(ls transcripts/*_fixed.txt 2>/dev/null | tail -1 || ls transcripts/*.txt | tail -1)
echo "    文稿: $TRANSCRIPT"

# ─ 第3步：仿写 ──────────────────────────────
echo ""
echo "[3/5] 仿写成高阳纺织风格..."
python 02-transcribe/rewrite.py \
  --input "$TRANSCRIPT" \
  --duration "$DURATION"
REWRITE=$(ls transcripts/*_rewrite_*.txt | tail -1)
echo "    仿写稿: $REWRITE"

# ─ 第4步：Remotion 渲染字幕动画 ──────────────
echo ""
echo "[4/5] 渲染字幕动画视频..."
echo "    ⚠️  请先手动把仿写稿更新到 03-remotion/src/Root/sampleScript.ts"
echo "    然后运行: cd 03-remotion && npm install && npm run render"
echo "    渲染完成后视频在 03-remotion/out/video.mp4"
# cd 03-remotion && npm run render  # 取消注释可自动执行

# ─ 第5步：分发 ──────────────────────────────
echo ""
echo "[5/5] 发布到平台..."
echo "    ⚠️  请先配置 04-distribute/cookies/ 下各平台的 cookie"
echo "    然后运行: python 04-distribute/distribute.py --config 04-distribute/publish.json"
# python 04-distribute/distribute.py --config 04-distribute/publish.json  # 取消注释可自动执行

echo ""
echo "========================================="
echo "✅ 流水线完成（步骤4和5需手动执行，见上方提示）"
echo "========================================="
