import { useEffect, useRef, useState, useCallback } from 'react';
import uPlot from 'uplot';

export interface UplotOptions {
  width: number;
  height: number;
  series: uPlot.Series[];
  scales?: Record<string, uPlot.Scale>;
  axes?: uPlot.Axis[];
  hooks?: uPlot.Hooks.Arrays;
  cursor?: uPlot.Cursor;
  plugins?: uPlot.Plugin[];
}

export function useUplot(
  data: uPlot.AlignedData,
  options: UplotOptions,
  deps: any[] = []
) {
  const containerRef = useRef<HTMLDivElement>(null);
  const plotRef = useRef<uPlot | null>(null);
  const [isReady, setIsReady] = useState(false);

  // Initialize uPlot
  useEffect(() => {
    if (!containerRef.current) return;

    const plot = new uPlot(options, data, containerRef.current);
    plotRef.current = plot;
    setIsReady(true);

    return () => {
      plot.destroy();
      plotRef.current = null;
      setIsReady(false);
    };
  }, [containerRef.current, ...deps]);

  // Update data
  useEffect(() => {
    if (plotRef.current && isReady) {
      plotRef.current.setData(data);
    }
  }, [data, isReady]);

  // Resize handler
  const handleResize = useCallback((width: number, height: number) => {
    if (plotRef.current) {
      plotRef.current.setSize({ width, height });
    }
  }, []);

  // Update scale
  const setScale = useCallback((key: string, opts: { min: number; max: number }) => {
    if (plotRef.current) {
      plotRef.current.setScale(key, opts);
    }
  }, []);

  return {
    containerRef,
    plotRef,
    isReady,
    handleResize,
    setScale,
  };
}
