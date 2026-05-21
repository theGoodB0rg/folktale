import {AbsoluteFill, OffthreadVideo} from 'remotion';
import type {MotionShot} from '../lib/blueprint';
import {resolveEpisodeAsset} from '../lib/blueprint';

type MotionClipProps = {
  shot: MotionShot;
  episodeRoot?: string;
};

export const MotionClip = ({shot, episodeRoot}: MotionClipProps) => {
  const videoSrc = resolveEpisodeAsset(shot.asset_path, episodeRoot);

  return (
    <AbsoluteFill style={{backgroundColor: '#111'}}>
      <OffthreadVideo
        src={videoSrc}
        muted
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
        }}
      />
    </AbsoluteFill>
  );
};
