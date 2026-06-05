#!/usr/bin/env bash
# 渲染字幕动画成品视频
# 自动探测可用的 Chromium，规避 Remotion 下载 chrome-headless-shell 的网络限制
# 用法:
#   ./render.sh [输出文件名] [props.json]
#   ./render.sh out/video.mp4 props.json   # 用自定义文案/配音渲染

set -e
cd "$(dirname "$0")"

OUT="${1:-out/video.mp4}"
PROPS="${2:-}"

PROPS_FLAG=""
if [ -n "$PROPS" ] && [ -f "$PROPS" ]; then
  PROPS_FLAG="--props=$PROPS"
  echo "使用自定义 props: $PROPS"
fi

# ── 探测系统已装的 Chromium/Chrome（按优先级）────────────────
# 注意: command -v 在未找到时返回非零，需配合 || true 避免 set -e 退出
CHROME=""
for c in /opt/pw-browsers/chromium-*/chrome-linux/chrome \
         "$(command -v chromium || true)" \
         "$(command -v chromium-browser || true)" \
         "$(command -v google-chrome || true)" \
         "$(command -v google-chrome-stable || true)"; do
  if [ -n "$c" ] && [ -x "$c" ]; then CHROME="$c"; break; fi
done

if [ -z "$CHROME" ]; then
  echo "未找到系统 Chromium。Remotion 会尝试自行下载（需要网络放行 remotion.media）。"
  npx remotion render src/index.ts VideoComposition "$OUT" $PROPS_FLAG
else
  echo "使用 Chromium: $CHROME"
  # chrome-for-testing 模式 → 用新版 --headless=new，兼容新版 Chrome
  npx remotion render src/index.ts VideoComposition "$OUT" $PROPS_FLAG \
    --browser-executable="$CHROME" \
    --chrome-mode="chrome-for-testing" \
    --gl="angle"
fi

echo "✅ 渲染完成: $OUT"
