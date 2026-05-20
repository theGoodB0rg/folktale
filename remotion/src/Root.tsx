import {Composition} from 'remotion';
import {FolktaleEpisode} from './compositions/FolktaleEpisode';
import {
  type FolktaleEpisodeProps,
  folktaleEpisodePropsSchema,
  getBlueprintDurationSeconds,
  getBlueprintFps,
} from './lib/blueprint';
import {secondsToFrames} from './lib/timeline';

const DEFAULT_FPS = 30;
const DEFAULT_WIDTH = 1280;
const DEFAULT_HEIGHT = 720;
const DEFAULT_DURATION_SECONDS = 6;

const defaultProps: FolktaleEpisodeProps = {};

export const RemotionRoot = () => {
  return (
    <Composition<typeof folktaleEpisodePropsSchema, FolktaleEpisodeProps>
      id="FolktaleEpisode"
      component={FolktaleEpisode}
      schema={folktaleEpisodePropsSchema}
      fps={DEFAULT_FPS}
      width={DEFAULT_WIDTH}
      height={DEFAULT_HEIGHT}
      durationInFrames={secondsToFrames(DEFAULT_DURATION_SECONDS, DEFAULT_FPS)}
      defaultProps={defaultProps}
      calculateMetadata={({props}) => {
        const fps = getBlueprintFps(props.blueprint, DEFAULT_FPS);
        const durationSeconds = getBlueprintDurationSeconds(
          props.blueprint,
          DEFAULT_DURATION_SECONDS,
        );

        return {
          fps,
          durationInFrames: Math.max(1, secondsToFrames(durationSeconds, fps)),
          width: props.blueprint?.render.preview.width ?? DEFAULT_WIDTH,
          height: props.blueprint?.render.preview.height ?? DEFAULT_HEIGHT,
        };
      }}
    />
  );
};
