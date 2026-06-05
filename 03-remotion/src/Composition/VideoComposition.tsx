import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { PillBar } from "./PillBar";
import { SubtitleCard } from "./SubtitleCard";
import { VideoConfig } from "./types";

// ─── 背景：深色网格 ──────────────────────────────────────────────────────────
const DarkGridBg: React.FC<{ color?: string }> = ({ color = "#0d0d1a" }) => (
  <AbsoluteFill
    style={{
      background: color,
      backgroundImage: `
        linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px)
      `,
      backgroundSize: "60px 60px",
    }}
  />
);

// ─── 顶部标签栏 ──────────────────────────────────────────────────────────────
const TagLine: React.FC<{ text: string }> = ({ text }) => (
  <div
    style={{
      position: "absolute",
      top: 36,
      left: 0,
      right: 0,
      display: "flex",
      justifyContent: "center",
    }}
  >
    <div
      style={{
        background: "rgba(255,255,255,0.07)",
        border: "1px solid rgba(255,255,255,0.15)",
        borderRadius: 999,
        padding: "8px 32px",
        color: "rgba(255,255,255,0.7)",
        fontSize: 26,
        fontFamily: "'PingFang SC', 'Noto Sans SC', sans-serif",
        letterSpacing: 2,
      }}
    >
      {text}
    </div>
  </div>
);

// ─── AI 标识水印（合规要求）─────────────────────────────────────────────────
const AiLabel: React.FC = () => (
  <div
    style={{
      position: "absolute",
      bottom: 50,
      right: 40,
      color: "rgba(255,255,255,0.3)",
      fontSize: 22,
      fontFamily: "monospace",
    }}
  >
    AI 生成内容
  </div>
);

// ─── 主合成组件 ──────────────────────────────────────────────────────────────
export const VideoComposition: React.FC<VideoConfig> = ({
  tagLine = "AI落地 · 纺织商家专属",
  pills,
  segments,
  bgColor,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 根据当前帧判断激活的 pill
  const currentSeg = segments.find(
    (s) => frame >= s.from && frame < s.from + s.durationInFrames
  );
  const activePillIndex = currentSeg
    ? Math.floor((segments.indexOf(currentSeg) / segments.length) * (pills?.length ?? 1))
    : undefined;

  return (
    <AbsoluteFill>
      <DarkGridBg color={bgColor} />
      <TagLine text={tagLine} />

      {pills && pills.length > 0 && (
        <PillBar pills={pills} frame={frame} activePillIndex={activePillIndex} />
      )}

      {segments.map((seg, i) => (
        <Sequence
          key={i}
          from={seg.from}
          durationInFrames={seg.durationInFrames}
          layout="none"
        >
          <SubtitleCard
            segment={seg}
            localFrame={frame - seg.from}
          />
        </Sequence>
      ))}

      <AiLabel />
    </AbsoluteFill>
  );
};
