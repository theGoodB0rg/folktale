import {AbsoluteFill, Img, interpolate, useCurrentFrame} from 'remotion';
import type {Scene} from '../lib/blueprint';
import {resolveEpisodeAsset} from '../lib/blueprint';

type SceneStillProps = {
  scene: Scene;
  episodeRoot?: string;
};

export const SceneStill = ({scene, episodeRoot}: SceneStillProps) => {
  const frame = useCurrentFrame();
  const scale = interpolate(frame, [0, 180], [1, 1.05], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{backgroundColor: '#16120f', overflow: 'hidden'}}>
      <Img
        src={resolveEpisodeAsset(scene.asset_path, episodeRoot)}
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'cover',
          transform: `scale(${scale})`,
        }}
      />
    </AbsoluteFill>
  );
};
