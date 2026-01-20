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
      padding: [10, 0, 10, 0],
      scales: {
        x: {
          time: false,
          range: [viewport.start, viewport.end],
        },
        y: {
          range: yMin !== null && yMax !== null ? [yMin, yMax] : undefined,
        },
      },
      // Enable uPlot native cursor and nearest-point highlighting
      cursor: {
        show: true,
        x: true,
        y: false,
        lock: false,
        points: {
          show: (u, sidx, idx) => typeof idx === 'number' && idx >= 0,
          size: 6,
          stroke: '#ffffff',
        },
      },
      hooks: {
        setCursor: [
          (u: uPlot) => {
            try {
              const idx = (u.cursor && (u.cursor.idx as number | null)) ?? null;
              if (typeof idx === 'number' && idx >= 0) {
                const time = (u.data[0] as number[])[idx];
                onSharedMouseMove?.(Math.round(time * 10) / 10);
              } else {
                onSharedMouseMove?.(null);
              }
            } catch (e) {
              // ignore
            }
          },
        ],
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
        {}, // x-axis series
        {
          label: `${channel.toUpperCase()}-X`,
          stroke: colors[channel].x,
          width: 1.5,  // 细线条
          points: { show: false },  // 静态点不显示
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
        show: false,
        drag: { x: false, y: false },
        x: false,
        y: false,
        lock: false,
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

  // 简化版：使用 uPlot 的 posToIdx 直接获取最近点
  // uPlot 已经在内部处理点的高亮，这里只用于自定义 tooltip
  const computeNearestPoints = (mouseLeft: number | null) => {
    if (mouseLeft === null) return null;
    const plot = plotRef.current;
    if (!plot) return null;

    const times = uplotData[0] as number[];
    if (!times || times.length === 0) return null;

    try {
      // 直接使用 uPlot 的 posToIdx 获取最近索引
      const idx = plot.posToIdx(mouseLeft);
      if (idx == null || idx < 0 || idx >= times.length) return null;

      const time = times[idx];
      const xs = uplotData[1] as number[];
      const ys = uplotData[2] as number[];
      const zs = uplotData[3] as number[];

      // 使用 uPlot 的 valToPos 确保 100% 对齐
      const x = plot.valToPos(time, 'x');
      
      const pts = [
        {
          series: 'X',
          value: xs[idx],
          x,
          y: plot.valToPos(xs[idx], 'y'),
          color: colors[channel].x,
        },
        {
          series: 'Y',
          value: ys[idx],
          x,
          y: plot.valToPos(ys[idx], 'y'),
          color: colors[channel].y,
        },
        {
          series: 'Z',
          value: zs[idx],
          x,
          y: plot.valToPos(zs[idx], 'y'),
          color: colors[channel].z,
        },
      ];

      return { idx, time, x, points: pts };
    } catch (err) {
      return null;
    }
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

  const activeMouseX = mousePosition?.x ?? sharedMousePosition?.x ?? null;
  const nearestInfo = computeNearestPoints(activeMouseX);
  const overlayMousePosition = nearestInfo
    ? { x: nearestInfo.x, time: nearestInfo.time }
    : mousePosition ?? sharedMousePosition ?? null;

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
        <div 
          ref={uplotContainerRef} 
          style={{ 
            width: `${dimensions.width}px`, 
            height: `${dimensions.height}px`,
            position: 'relative'
          }} 
        />

        {/* 左上角通道名称（工业风格） */}
        <div className="absolute top-0 pointer-events-none" style={{ left: '50px' }}>
          <span className="text-4xl font-bold text-[#0E0E0E] opacity-25">
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
          mousePosition={overlayMousePosition}
          // nearest point info for crosshair tooltip/markers
          nearestInfo={nearestInfo}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseLeave}
          cursor={getCursorStyle()}
          useUplotNativeCursor={false}
        />

        {/* Canvas Tooltip in OverlayCanvas handles time and series values */}
      </div>
    </div>
  );
}
