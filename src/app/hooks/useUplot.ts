import { useEffect, useLayoutEffect, useRef, useState, useCallback } from 'react';
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

  // Initialize uPlot using useLayoutEffect to ensure DOM is measured
  useLayoutEffect(() => {
    const container = containerRef.current;
    
    // Destroy existing plot if any
    if (plotRef.current) {
      try {
        plotRef.current.destroy();
      } catch (e) {
        console.warn('Error destroying plot:', e);
      }
      plotRef.current = null;
      setIsReady(false);
    }

    // Strict validation
    if (!container || 
        !(container instanceof HTMLElement) || 
        !container.isConnected) {
      return;
    }
    
    try {
      const plot = new uPlot(options, data, container);
      plotRef.current = plot;
      setIsReady(true);
    } catch (error) {
      console.error('Failed to initialize uPlot:', error);
    }

    return () => {
      if (plotRef.current) {
        try {
          plotRef.current.destroy();
        } catch (e) {
          console.warn('Error destroying plot:', e);
        }
        plotRef.current = null;
      }
      setIsReady(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

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
