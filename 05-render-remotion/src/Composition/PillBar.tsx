import React from "react";
import { interpolate, spring, useVideoConfig } from "remotion";
import { PillLabel } from "./types";

interface Props {
  pills: PillLabel[];
  frame: number;
  activePillIndex?: number;
}

export const PillBar: React.FC<Props> = ({ pills, frame, activePillIndex }) => {
  const { fps } = useVideoConfig();

  return (
    <div
      style={{
        position: "absolute",
        top: 90,
        left: 0,
        right: 0,
        display: "flex",
        justifyContent: "center",
        gap: 16,
        padding: "0 40px",
        flexWrap: "wrap",
      }}
    >
      {pills.map((pill, i) => {
        const entryFrame = i * 4;
        const entered = spring({
          fps,
          frame: Math.max(0, frame - entryFrame),
          config: { damping: 16, stiffness: 200 },
          durationInFrames: 18,
        });
        const scale = interpolate(entered, [0, 1], [0.5, 1]);
        const isActive = activePillIndex === i;

        return (
          <div
            key={i}
            style={{
              background: isActive ? pill.color : `${pill.color}33`,
              border: `2px solid ${pill.color}`,
              borderRadius: 999,
              padding: "10px 24px",
              color: isActive ? "#fff" : pill.color,
              fontWeight: 700,
              fontSize: 28,
              fontFamily: "'PingFang SC', 'Noto Sans SC', sans-serif",
              transform: `scale(${scale})`,
              whiteSpace: "nowrap",
              transition: "background 0.3s",
            }}
          >
            {pill.text}
          </div>
        );
      })}
    </div>
  );
};
