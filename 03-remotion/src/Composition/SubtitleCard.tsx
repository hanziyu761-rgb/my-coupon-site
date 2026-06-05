import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { Segment } from "./types";

interface Props {
  segment: Segment;
  /** 该片段的本地帧（从 0 开始） */
  localFrame: number;
}

export const SubtitleCard: React.FC<Props> = ({ segment, localFrame }) => {
  const { fps } = useVideoConfig();

  // 入场弹性动画
  const enter = spring({
    fps,
    frame: localFrame,
    config: { damping: 14, stiffness: 180 },
    durationInFrames: 20,
  });

  // 出场淡出（最后10帧）
  const fadeOut = interpolate(
    localFrame,
    [segment.durationInFrames - 10, segment.durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const opacity = localFrame < segment.durationInFrames - 10 ? 1 : fadeOut;
  const translateY = interpolate(enter, [0, 1], [40, 0]);

  // 关键词高亮
  const renderText = () => {
    if (!segment.highlight) {
      return <span>{segment.text}</span>;
    }
    const parts = segment.text.split(segment.highlight);
    return (
      <>
        {parts.map((part, i) => (
          <React.Fragment key={i}>
            {part}
            {i < parts.length - 1 && (
              <span style={{ color: "#FFD700", fontWeight: 800 }}>
                {segment.highlight}
              </span>
            )}
          </React.Fragment>
        ))}
      </>
    );
  };

  return (
    <AbsoluteFill
      style={{
        justifyContent: "flex-end",
        alignItems: "center",
        paddingBottom: 120,
        opacity,
        transform: `translateY(${translateY}px)`,
      }}
    >
      <div
        style={{
          background: "rgba(0,0,0,0.75)",
          backdropFilter: "blur(6px)",
          borderRadius: 18,
          padding: "22px 36px",
          maxWidth: "82%",
          textAlign: "center",
          border: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        <span
          style={{
            fontSize: 52,
            fontWeight: 700,
            color: "#FFFFFF",
            lineHeight: 1.35,
            fontFamily: "'PingFang SC', 'Noto Sans SC', sans-serif",
            letterSpacing: 1,
          }}
        >
          {renderText()}
        </span>
      </div>
    </AbsoluteFill>
  );
};
