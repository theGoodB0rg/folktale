import {AbsoluteFill, useCurrentFrame} from 'remotion';
import type {NarrationSegment} from '../lib/blueprint';
import {secondsToFrames} from '../lib/timeline';

type CaptionLayerProps = {
  segments: NarrationSegment[];
  fps: number;
};

export const CaptionLayer = ({segments, fps}: CaptionLayerProps) => {
  const frame = useCurrentFrame();
  const activeSegment = segments.find((segment) => {
    const start = secondsToFrames(segment.start_sec, fps);
    const end = start + secondsToFrames(segment.target_duration_sec, fps);
    return frame >= start && frame < end;
  });

  if (!activeSegment) {
    return null;
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
        padding: 48,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          maxWidth: 960,
          color: 'white',
          backgroundColor: 'rgba(12, 12, 12, 0.72)',
          fontFamily: 'Arial, Helvetica, sans-serif',
          fontSize: 34,
          lineHeight: 1.25,
          padding: '18px 24px',
          textAlign: 'center',
        }}
      >
        {activeSegment.text}
      </div>
    </AbsoluteFill>
  );
};
