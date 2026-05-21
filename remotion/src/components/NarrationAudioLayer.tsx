import {Audio, Sequence} from 'remotion';
import type {NarrationSegment} from '../lib/blueprint';
import {resolveEpisodeAsset} from '../lib/blueprint';
import {secondsToFrames} from '../lib/timeline';

type NarrationAudioLayerProps = {
  segments: NarrationSegment[];
  episodeRoot?: string;
  fps: number;
};

export const NarrationAudioLayer = ({
  segments,
  episodeRoot,
  fps,
}: NarrationAudioLayerProps) => {
  return (
    <>
      {segments.map((segment) => {
        const startFrame = secondsToFrames(segment.start_sec, fps);
        const durationInFrames = Math.max(
          1,
          secondsToFrames(segment.target_duration_sec, fps),
        );

        return (
          <Sequence
            key={segment.id}
            from={startFrame}
            durationInFrames={durationInFrames}
          >
            <Audio
              src={resolveEpisodeAsset(segment.audio_path, episodeRoot)}
            />
          </Sequence>
        );
      })}
    </>
  );
};
