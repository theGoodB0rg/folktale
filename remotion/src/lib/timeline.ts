export const secondsToFrames = (seconds: number, fps: number): number => {
  if (!Number.isFinite(seconds) || seconds < 0) {
    throw new Error('seconds must be a finite non-negative number');
  }

  if (!Number.isFinite(fps) || fps <= 0) {
    throw new Error('fps must be a finite positive number');
  }

  return Math.round(seconds * fps);
};
