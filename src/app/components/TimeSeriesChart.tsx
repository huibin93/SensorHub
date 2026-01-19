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
  toolMode,
  onViewportChange,
  yAxisDomain,
}: TimeSeriesChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 250 });
  const [mousePosition, setMousePosition] = useState<{ x: number; time: number } | null>(null);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const [isHovering, setIsHovering] = useState(false);
  const { pixelToTime, timeToPixel } = useRegions();

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
    const time = pixelToTime(x, viewport.start, viewport.end, dimensions.width);

    if (toolMode === 'annotate' || toolMode === 'zoom') {
      setDragStart(time);
      setDragEnd(time);
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!plotRef.current) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const time = pixelToTime(x, viewport.start, viewport.end, dimensions.width);

    setMousePosition({ x, time });

    if (dragStart !== null) {
      setDragEnd(time);
    }
  };

  const handleCanvasMouseUp = () => {
    if (dragStart !== null && dragEnd !== null) {
      const minTime = Math.min(dragStart, dragEnd);
      const maxTime = Math.max(dragStart, dragEnd);

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
          dragSelection={dragSelection}
          mousePosition={mousePosition}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseLeave}
          cursor={getCursorStyle()}
          showVerticalLines={true}
        />

        {/* Time tooltip - \u8ddf\u968f\u9f20\u6807\u663e\u793a */}
        {mousePosition !== null && !dragStart && (
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
