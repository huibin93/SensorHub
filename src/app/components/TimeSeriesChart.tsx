import { useState, useRef, useEffect, useMemo } from 'react';
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';
import { TimeSeriesDataPoint, AnnotationRegion, LabelType } from '@/app/types';
import { ToolMode } from './ChartToolbar';
import { useUplot } from '../hooks/useUplot';
import { useRegions } from '../hooks/useRegions';
import { OverlayCanvas } from './OverlayCanvas';

interface TimeSeriesChartProps {
  data: TimeSeriesDataPoint[];
  viewport: { start: number; end: number };
  channel: 'acc' | 'gyro';
  annotations: AnnotationRegion[];
  selectedLabels: LabelType[];
  onCreateAnnotation: (startTime: number, endTime: number) => void;
  hoveredRegionId: string | null;
  selectedRegionId?: string | null;
  onHoverChange?: (id: string | null) => void;
  onRegionSelect?: (id: string | null) => void;
  onUpdateAnnotation?: (updated: AnnotationRegion) => void;
  // Shared crosshair time (for synchronized vertical line across charts)
  sharedMouseTime?: number | null;
  onSharedMouseMove?: (time: number | null) => void;
  toolMode: ToolMode;
  onViewportChange?: (viewport: { start: number; end: number }) => void;
  yAxisDomain?: [number, number] | null;
}

export function TimeSeriesChart({
  data,
  viewport,
  channel,
  annotations,
  selectedLabels,
  onCreateAnnotation,
  hoveredRegionId,
  selectedRegionId,
  onHoverChange,
  onRegionSelect,
  onUpdateAnnotation,
  sharedMouseTime,
  onSharedMouseMove,
  toolMode,
  onViewportChange,
  yAxisDomain,
}: TimeSeriesChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const roundToTenth = (v: number) => Math.round(v * 10) / 10;
  const [dimensions, setDimensions] = useState({ width: 800, height: 250 });
  const [mousePosition, setMousePosition] = useState<{ x: number; time: number } | null>(null);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const [isHovering, setIsHovering] = useState(false);
  const { pixelToTime, timeToPixel, hitTest } = useRegions();
  const [dragging, setDragging] = useState<{
    regionId: string;
    handle: 'left' | 'right' | 'body';
    origStart: number;
    origEnd: number;
    origMouseTime: number;
  } | null>(null);
  // If parent passed a shared mouse time, compute a mousePosition for overlay
  const sharedMousePosition = (() => {
    if (typeof sharedMouseTime === 'number') {
      // Always compute shared position (may be outside current viewport)
      const x = timeToPixel(sharedMouseTime, viewport.start, viewport.end, dimensions.width);
      return { x, time: sharedMouseTime } as { x: number; time: number };
    }
    return null;
  })();

  // Handle resize
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width, height: height - 30 });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Prepare data for uPlot
  const uplotData = useMemo((): uPlot.AlignedData => {
    // Filter data for viewport
    const filteredData = data.filter(
      (d) => d.time >= viewport.start && d.time <= viewport.end
    );

    const times = filteredData.map((d) => d.time);
    const xData = filteredData.map((d) => (channel === 'acc' ? d.accX : d.gyroX));
    const yData = filteredData.map((d) => (channel === 'acc' ? d.accY : d.gyroY));
    const zData = filteredData.map((d) => (channel === 'acc' ? d.accZ : d.gyroZ));

    return [times, xData, yData, zData];
  }, [data, viewport, channel]);

  // Colors for channels - High saturation colors
  const colors = {
    acc: { x: '#D32F2F', y: '#388E3C', z: '#1976D2' },  // 更高饱和度，更深的颜色
    gyro: { x: '#E65100', y: '#6A1B9A', z: '#00838F' },
  };

  // uPlot options
  const uplotOptions = useMemo((): uPlot.Options => {
    // Calculate Y axis range
    let yMin: number | null = null;
    let yMax: number | null = null;

    if (yAxisDomain) {
      [yMin, yMax] = yAxisDomain;
    }

    return {
      width: dimensions.width,
      height: dimensions.height,
      scales: {
        x: {
          time: false,
          range: [viewport.start, viewport.end],
        },
        y: {
          range: yMin !== null && yMax !== null ? [yMin, yMax] : undefined,
        },
      },
      axes: [
        {
          stroke: '#BDBDBD',
          grid: { stroke: '#F5F5F5', width: 1 },  // 更淡的网格线
          ticks: { stroke: '#BDBDBD' },
          // show integer tick labels without unit
          values: (u, vals) => vals.map((v) => `${Math.round(v)}`),
        },
        {
          stroke: '#BDBDBD',
          grid: { stroke: '#F5F5F5', width: 1 },
          ticks: { stroke: '#BDBDBD' },
        },
      ],
      series: [
        {},
        {
          label: `${channel.toUpperCase()}-X`,
          stroke: colors[channel].x,
          width: 1.5,  // 细线条
          points: { show: false },
        },
        {
          label: `${channel.toUpperCase()}-Y`,
          stroke: colors[channel].y,
          width: 1.5,
          points: { show: false },
        },
        {
          label: `${channel.toUpperCase()}-Z`,
          stroke: colors[channel].z,
          width: 1.5,
          points: { show: false },
        },
      ],
      cursor: {
        drag: { x: false, y: false },
        points: { show: false },
      },
      legend: { show: false },
    };
  }, [dimensions, viewport, channel, colors, yAxisDomain]);

  const { containerRef: uplotContainerRef, plotRef } = useUplot(
    uplotData,
    uplotOptions,
    [viewport, channel, yAxisDomain]
  );

  // Compute nearest points for crosshair tooltip using uPlot API when possible
  // Accept mouseLeft (CSS pixels relative to plotting area)
  const computeNearestPoints = (mouseLeft: number | null) => {
    if (mouseLeft === null) return null;
    const plot = plotRef.current as any;
    const times = uplotData[0] as number[];
    if (!times || times.length === 0) return null;

    // device pixel ratio
    const dpr = window.devicePixelRatio || 1;

    // Try to use uPlot APIs with canvas-pixel coordinates, then convert back to CSS pixels
    try {
      if (plot && typeof plot.posToIdx === 'function' && typeof plot.valToPos === 'function') {
        // uPlot's bbox values are in canvas pixels. Convert our mouse (CSS px)
        // into canvas px and query uPlot, then convert returned canvas px back
        // into CSS px for our overlay drawing (we draw in CSS pixels via ctx.scale(dpr,dpr)).
        const bbox = plot.bbox || { left: 0, top: 0 };

        // CSS -> canvas px
        const canvasX = mouseLeft * dpr + (bbox.left || 0);

        // nearest index
        let idx = plot.posToIdx(canvasX, /*canvasPixels=*/true);
        if (idx === null || idx === undefined) {
          const timeAt = pixelToTime(mouseLeft, viewport.start, viewport.end, dimensions.width);
          let lo = 0;
          let hi = times.length - 1;
          while (lo < hi) {
            const mid = Math.floor((lo + hi) / 2);
            if (times[mid] < timeAt) lo = mid + 1;
            else hi = mid;
          }
          idx = lo;
          if (idx > 0 && Math.abs(times[idx - 1] - timeAt) <= Math.abs(times[idx] - timeAt)) idx = idx - 1;
        }

        if (idx === null || idx === undefined) return null;

        const xs = uplotData[1] as number[];
        const ys = uplotData[2] as number[];
        const zs = uplotData[3] as number[];

        const seriesMeta = plot.series || [];
        const resolveScale = (seriesIdx: number) => {
          const meta = seriesMeta[seriesIdx];
          return (meta && meta.scale) || 'y';
        };

        // ask uPlot for canvas-pixel positions
        const timeCanvasPx = plot.valToPos(times[idx], /*scaleKey=*/'x', /*canvasPixels=*/true);
        const xCanvas = plot.valToPos(xs[idx], resolveScale(1), /*canvasPixels=*/true);
        const yCanvas = plot.valToPos(ys[idx], resolveScale(2), /*canvasPixels=*/true);
        const zCanvas = plot.valToPos(zs[idx], resolveScale(3), /*canvasPixels=*/true);

        // canvas px -> CSS px for our overlay
        const cssX = (timeCanvasPx - (bbox.left || 0)) / dpr;
        const pxX = (xCanvas - (bbox.left || 0)) / dpr;
        const pxY = (yCanvas - (bbox.top || 0)) / dpr;
        const pxZ = (zCanvas - (bbox.top || 0)) / dpr;

        const pts = [
          { series: 'X', value: xs[idx], x: cssX, y: pxX, color: colors[channel].x },
          { series: 'Y', value: ys[idx], x: cssX, y: pxY, color: colors[channel].y },
          { series: 'Z', value: zs[idx], x: cssX, y: pxZ, color: colors[channel].z },
        ];

        return { idx, time: times[idx], points: pts };
      }
    } catch (err) {
      // fall through to manual mapping
    }

    // Manual fallback
    const xs = uplotData[1] as number[];
    const ys = uplotData[2] as number[];
    const zs = uplotData[3] as number[];
    const timeAt = pixelToTime(mouseLeft, viewport.start, viewport.end, dimensions.width);
    let lo = 0;
    let hi = times.length - 1;
    while (lo < hi) {
      const mid = Math.floor((lo + hi) / 2);
      if (times[mid] < timeAt) lo = mid + 1;
      else hi = mid;
    }
    let idx = lo;
    if (idx > 0 && Math.abs(times[idx - 1] - timeAt) <= Math.abs(times[idx] - timeAt)) idx = idx - 1;

    const values = [...xs, ...ys, ...zs];
    let yMin = Math.min(...values);
    let yMax = Math.max(...values);
    if (yMin === yMax) {
      yMin -= 1;
      yMax += 1;
    }

    const x = timeToPixel(times[idx], viewport.start, viewport.end, dimensions.width);
    const valueToPixel = (v: number) => {
      const ratio = (v - yMin) / (yMax - yMin);
      return dimensions.height - ratio * dimensions.height;
    };

    const pts = [
      { series: 'X', value: xs[idx], x, y: valueToPixel(xs[idx]), color: colors[channel].x },
      { series: 'Y', value: ys[idx], x, y: valueToPixel(ys[idx]), color: colors[channel].y },
      { series: 'Z', value: zs[idx], x, y: valueToPixel(zs[idx]), color: colors[channel].z },
    ];

    return { idx, time: times[idx], points: pts };
  };

  // Get cursor style based on tool mode and hover state
  const getCursorStyle = () => {
    if (isHovering) return 'crosshair';
    if (toolMode === 'pan') return 'grab';
    if (toolMode === 'zoom') return 'crosshair';
    if (toolMode === 'annotate') return 'cell';
    return 'default';
  };

  // Handle mouse events
  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!plotRef.current) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const time = pixelToTime(x, viewport.start, viewport.end, dimensions.width);

    // Hit test for region selection on mouse down
    const hit = hitTest(x, y, annotations, viewport, dimensions.width, dimensions.height);
    if (hit.region) {
      onRegionSelect?.(hit.region.id);

      // If clicked on a handle or body and the region is selected, start dragging
      if (hit.handle && selectedRegionId === hit.region.id) {
        setDragging({
          regionId: hit.region.id,
          handle: hit.handle,
          origStart: hit.region.startTime,
          origEnd: hit.region.endTime,
          origMouseTime: time,
        });
      }
    } else {
      // Clicked blank area -> clear selection
      onRegionSelect?.(null);
    }

    if (toolMode === 'annotate' || toolMode === 'zoom') {
      const t = roundToTenth(time);
      setDragStart(t);
      setDragEnd(t);
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!plotRef.current) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const time = pixelToTime(x, viewport.start, viewport.end, dimensions.width);
    const timeRounded = roundToTenth(time);

    setMousePosition({ x, time: timeRounded });

    // Report shared mouse time upstream for synchronized crosshair (snapped)
    if (onSharedMouseMove) {
      onSharedMouseMove(timeRounded);
    }

    // Hit test for hover state and notify parent
    if (onHoverChange) {
      const hit = hitTest(x, y, annotations, viewport, dimensions.width, dimensions.height);
      onHoverChange(hit.region ? hit.region.id : null);
    }

    // Handle dragging update
    if (dragging && onUpdateAnnotation) {
      const region = annotations.find(a => a.id === dragging.regionId);
      if (region) {
        const minDuration = 0.1;
        let newStart = dragging.origStart;
        let newEnd = dragging.origEnd;
        const delta = timeRounded - dragging.origMouseTime;

        if (dragging.handle === 'body') {
          newStart = dragging.origStart + delta;
          newEnd = dragging.origEnd + delta;
        } else if (dragging.handle === 'left') {
          newStart = Math.min(dragging.origEnd - minDuration, timeRounded);
          newEnd = dragging.origEnd;
        } else if (dragging.handle === 'right') {
          newStart = dragging.origStart;
          newEnd = Math.max(dragging.origStart + minDuration, timeRounded);
        }

        // Ensure start <= end
        if (newEnd <= newStart) {
          if (dragging.handle === 'left') newStart = newEnd - minDuration;
          if (dragging.handle === 'right') newEnd = newStart + minDuration;
        }

        // Snap updated region times to 0.1s grid as well
        const updated: AnnotationRegion = { ...region, startTime: roundToTenth(newStart), endTime: roundToTenth(newEnd) };
        onUpdateAnnotation(updated);
      }
    }

    if (dragStart !== null) {
      setDragEnd(timeRounded);
    }
  };

  const handleCanvasMouseUp = () => {
    // Stop dragging
    setDragging(null);

    if (dragStart !== null && dragEnd !== null) {
      const minTime = Math.min(dragStart, dragEnd);
      const maxTime = Math.max(dragStart, dragEnd);

      // already snapped while dragging; ensure min difference check uses snapped values
      if (Math.abs(maxTime - minTime) > 0.5) {
        if (toolMode === 'annotate') {
          onCreateAnnotation(minTime, maxTime);
        } else if (toolMode === 'zoom') {
          onViewportChange?.({ start: minTime, end: maxTime });
        }
      }
    }

    setDragStart(null);
    setDragEnd(null);
  };

  const handleCanvasMouseLeave = () => {
    setMousePosition(null);
    setDragStart(null);
    setDragEnd(null);
    // Notify hover cleared
    if (onHoverChange) onHoverChange(null);
    // Clear shared crosshair when leaving chart
    if (onSharedMouseMove) onSharedMouseMove(null);
  };

  // Handle right-click zoom out
  const handleContextMenu = (e: React.MouseEvent) => {
    if (toolMode === 'zoom') {
      e.preventDefault();
      const duration = viewport.end - viewport.start;
      const center = (viewport.start + viewport.end) / 2;
      const newDuration = duration * 1.5;

      const minTime = Math.min(...data.map((d) => d.time));
      const maxTime = Math.max(...data.map((d) => d.time));

      let newStart = center - newDuration / 2;
      let newEnd = center + newDuration / 2;

      newStart = Math.max(minTime, newStart);
      newEnd = Math.min(maxTime, newEnd);

      onViewportChange?.({ start: newStart, end: newEnd });
    }
  };

  // Prepare drag selection for overlay
  const dragSelection =
    dragStart !== null && dragEnd !== null
      ? {
          start: dragStart,
          end: dragEnd,
          color:
            toolMode === 'zoom'
              ? '#909399'
              : selectedLabels[0]?.color || '#1890FF',
        }
      : null;

  const nearestInfo = computeNearestPoints(
    // prefer local mouse x, else shared mouse x
    mousePosition?.x ?? sharedMousePosition?.x ?? null
  );

  return (
    <div
      ref={containerRef}
      className="relative bg-white h-[300px]"
      onContextMenu={handleContextMenu}
      style={{ cursor: getCursorStyle() }}
    >

      <div 
        className="relative" 
        style={{ width: dimensions.width, height: dimensions.height }}
        onMouseEnter={() => setIsHovering(true)}
        onMouseLeave={() => setIsHovering(false)}
      >
        {/* uPlot chart */}
        <div ref={uplotContainerRef} />

        {/* 左上角通道名称（工业风格） */}
        <div className="absolute top-2 left-2 pointer-events-none">
          <span className="text-4xl font-bold text-[#BDBDBD] opacity-25">
            {channel.toUpperCase()}
          </span>
        </div>

        {/* 右上角图例 */}
        <div className="absolute top-2 right-2 flex gap-3 pointer-events-none">
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5" style={{ backgroundColor: colors[channel].x }} />
            <span className="text-xs font-medium" style={{ color: colors[channel].x }}>X</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5" style={{ backgroundColor: colors[channel].y }} />
            <span className="text-xs font-medium" style={{ color: colors[channel].y }}>Y</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-3 h-0.5" style={{ backgroundColor: colors[channel].z }} />
            <span className="text-xs font-medium" style={{ color: colors[channel].z }}>Z</span>
          </div>
        </div>

        {/* Overlay canvas for annotations */}
        <OverlayCanvas
          width={dimensions.width}
          height={dimensions.height}
          annotations={annotations}
          viewport={viewport}
          hoveredRegionId={hoveredRegionId}
          selectedRegionId={selectedRegionId}
          dragSelection={dragSelection}
          // mousePosition prefers local mouse over shared position
          mousePosition={mousePosition ?? sharedMousePosition}
          // nearest point info for crosshair tooltip/markers
          nearestInfo={nearestInfo}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseLeave}
          cursor={getCursorStyle()}
          showVerticalLines={true}
        />

        {/* Time tooltip - \u8ddf\u968f\u9f20\u6807\u663e\u793a */}
        {mousePosition !== null && !dragStart && !nearestInfo && (
          <div
            className="absolute bg-[#2C3E50] text-white text-xs px-2 py-1 rounded pointer-events-none z-20 shadow-lg"
            style={{
              left: `${mousePosition.x + 10}px`,
              top: '5px',
              transform: mousePosition.x > dimensions.width - 80 ? 'translateX(-100%)' : 'none',
            }}
          >
            T+{mousePosition.time.toFixed(2)}s
          </div>
        )}
      </div>
    </div>
  );
}
