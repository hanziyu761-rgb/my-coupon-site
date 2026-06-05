#!/usr/bin/env bash
# 渲染字幕动画成品视频
# 自动探测可用的 Chromium，规避 Remotion 下载 chrome-headless-shell 的网络限制
# 用法: ./render.sh [输出文件名]

set -e
cd "$(dirname "$0")"

OUT="${1:-out/video.mp4}"

# ── 探测系统已装的 Chromium/Chrome（按优先级）────────────────
CANDIDATES=(
  "/opt/pw-browsers/chromium-"*/chrome-linux/chrome   # Playwright
  "$(command -v chromium 2>/dev/null)"
  "$(command -v chromium-browser 2>/dev/null)"
  "$(command -v google-chrome 2>/dev/null)"
  "$(command -v google-chrome-stable 2>/dev/null)"
)

CHROME=""
for c in ${CANDIDATES[@]}; do
  if [ -n "$c" ] && [ -x "$c" ]; then CHROME="$c"; break; fi
done

if [ -z "$CHROME" ]; then
  echo "未找到系统 Chromium。Remotion 会尝试自行下载（需要网络放行 remotion.media）。"
  npx remotion render src/index.ts VideoComposition "$OUT"
else
  echo "使用 Chromium: $CHROME"
  # chrome-for-testing 模式 → 用新版 --headless=new，兼容新版 Chrome
  npx remotion render src/index.ts VideoComposition "$OUT" \
    --browser-executable="$CHROME" \
    --chrome-mode="chrome-for-testing" \
    --gl="angle"
fi

echo "✅ 渲染完成: $OUT"
