import { useCallback } from 'react';
import { AnnotationRegion } from '../types';

export interface RegionHitTest {
  region: AnnotationRegion | null;
  handle: 'left' | 'right' | 'body' | null;
}

export function useRegions() {
  // Convert time to pixel position
  const timeToPixel = useCallback(
    (time: number, minTime: number, maxTime: number, width: number): number => {
      const ratio = (time - minTime) / (maxTime - minTime);
      return ratio * width;
    },
    []
  );

  // Convert pixel to time
  const pixelToTime = useCallback(
    (pixel: number, minTime: number, maxTime: number, width: number): number => {
      const ratio = pixel / width;
      return minTime + ratio * (maxTime - minTime);
    },
    []
  );

  // Hit test for region (check if mouse is over region or handle)
  const hitTest = useCallback(
    (
      mouseX: number,
      mouseY: number,
      regions: AnnotationRegion[],
      viewport: { start: number; end: number },
      chartWidth: number,
      chartHeight: number,
      handleThreshold: number = 8
    ): RegionHitTest => {
      for (const region of regions) {
        // Skip regions outside viewport
        if (region.endTime < viewport.start || region.startTime > viewport.end) {
          continue;
        }

        const startX = timeToPixel(region.startTime, viewport.start, viewport.end, chartWidth);
        const endX = timeToPixel(region.endTime, viewport.start, viewport.end, chartWidth);

        // Check if mouse is within vertical bounds (full chart height)
        if (mouseY < 0 || mouseY > chartHeight) continue;

        // Check left handle
        if (Math.abs(mouseX - startX) <= handleThreshold) {
          return { region, handle: 'left' };
        }

        // Check right handle
        if (Math.abs(mouseX - endX) <= handleThreshold) {
          return { region, handle: 'right' };
        }

        // Check body
        if (mouseX >= startX && mouseX <= endX) {
          return { region, handle: 'body' };
        }
      }

      return { region: null, handle: null };
    },
    [timeToPixel]
  );

  return {
    timeToPixel,
    pixelToTime,
    hitTest,
  };
}
