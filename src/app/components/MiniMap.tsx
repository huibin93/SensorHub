import { useRef, useState, useEffect, useMemo } from 'react';
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';
import { TimeSeriesDataPoint, AnnotationRegion } from '@/app/types';
import { useUplot } from '../hooks/useUplot';

interface MiniMapProps {
  data: TimeSeriesDataPoint[];
  totalDuration: number;
  viewport: { start: number; end: number };
  onViewportChange: (viewport: { start: number; end: number }) => void;
  annotations?: AnnotationRegion[];  // 新增：标注区域
}

export function MiniMap({ data, totalDuration, viewport, onViewportChange, annotations = [] }: MiniMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState<'left' | 'right' | null>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [initialViewport, setInitialViewport] = useState(viewport);
  const [dimensions, setDimensions] = useState({ width: 800, height: 100 });
  const [isSelecting, setIsSelecting] = useState(false);
  const [selectionStart, setSelectionStart] = useState<number | null>(null);
  const [selectionEnd, setSelectionEnd] = useState<number | null>(null);

  // 获取数据的实际时间范围（确保 MiniMap 显示所有数据）
  const dataMin = useMemo(() => data.length > 0 ? data[0].time : 0, [data]);
  const dataMax = useMemo(() => data.length > 0 ? data[data.length - 1].time : totalDuration, [data, totalDuration]);

  // Handle resize
  useEffect(() => {
    if (!containerRef.current) return;

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width, height });
      }
    });

    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Downsample data for minimap
  const downsampledData = useMemo(() => {
    return data.filter((_, i) => i % 10 === 0);
  }, [data]);

  // Prepare data for uPlot
  const uplotData = useMemo((): uPlot.AlignedData => {
    const times = downsampledData.map((d) => d.time);
    const accX = downsampledData.map((d) => d.accX);
    return [times, accX];
  }, [downsampledData]);

  // uPlot options
  const axisHeight = 20; // px reserved inside minimap for x-axis labels

  const uplotOptions = useMemo((): uPlot.Options => {
    // ensure the minimap spans the full timeline: include totalDuration
    const fullMin = Math.min(dataMin, 0);
    const fullMax = Math.max(dataMax, totalDuration);

    return {
      width: dimensions.width,
      // make uPlot use the full available height minus our internal axis band
      height: Math.max(24, dimensions.height - axisHeight),
      scales: {
        x: {
          time: false,
          range: [fullMin, fullMax],  // 使用包含 totalDuration 的完整时间范围
        },
      },
      // hide uPlot's built-in x-axis so we can render labels inside the box
      axes: [
        { show: false },
        { show: false },
      ],
      series: [
        {},
        {
          stroke: '#757575',
          width: 1,
          points: { show: false },
        },
      ],
      cursor: { show: false },
      legend: { show: false },
    };
  }, [dimensions, dataMin, dataMax, totalDuration]);

  const { containerRef: uplotContainerRef } = useUplot(uplotData, uplotOptions, [dataMin, dataMax]);
  // 计算百分比位置的辅助函数（确保对齐）
  const getLeftPercent = (time: number) => {
    return ((time - dataMin) / (dataMax - dataMin)) * 100;
  };
  const getTimeFromPosition = (clientX: number): number => {
    if (!containerRef.current) return dataMin;
    const rect = containerRef.current.getBoundingClientRect();
    const ratio = (clientX - rect.left) / rect.width;
    return Math.max(dataMin, Math.min(dataMax, dataMin + ratio * (dataMax - dataMin)));
  };

  const handleMouseDown = (e: React.MouseEvent, type: 'drag' | 'left' | 'right') => {
    e.preventDefault();
    setDragStartX(e.clientX);
    setInitialViewport(viewport);
    
    if (type === 'drag') {
      setIsDragging(true);
    } else {
      setIsResizing(type);
    }
  };

  // 添加左键框选功能
  const handleContainerMouseDown = (e: React.MouseEvent) => {
    // 如果点击的是容器本身（不是选框）
    if (e.target === e.currentTarget || (e.target as HTMLElement).classList.contains('minimap-background')) {
      e.preventDefault();
      const startTime = getTimeFromPosition(e.clientX);
      setIsSelecting(true);
      setSelectionStart(startTime);
      setSelectionEnd(startTime);
      setDragStartX(e.clientX);
    }
  };

  const handleMouseMove = (e: MouseEvent) => {
    if (!containerRef.current) return;

    // 处理框选
    if (isSelecting && selectionStart !== null) {
      const currentTime = getTimeFromPosition(e.clientX);
      setSelectionEnd(currentTime);
      return;
    }

    const rect = containerRef.current.getBoundingClientRect();
    const deltaX = e.clientX - dragStartX;
    const deltaTime = (deltaX / rect.width) * (dataMax - dataMin);

    if (isDragging) {
      const duration = viewport.end - viewport.start;
      let newStart = initialViewport.start + deltaTime;
      let newEnd = initialViewport.end + deltaTime;

      // Clamp to bounds
      if (newStart < dataMin) {
        newStart = dataMin;
        newEnd = dataMin + duration;
      }
      if (newEnd > dataMax) {
        newEnd = dataMax;
        newStart = dataMax - duration;
      }

      onViewportChange({ start: newStart, end: newEnd });
    } else if (isResizing === 'left') {
      const newStart = Math.max(dataMin, Math.min(initialViewport.end - 1, initialViewport.start + deltaTime));
      onViewportChange({ start: newStart, end: viewport.end });
    } else if (isResizing === 'right') {
      const newEnd = Math.min(dataMax, Math.max(initialViewport.start + 1, initialViewport.end + deltaTime));
      onViewportChange({ start: viewport.start, end: newEnd });
    }
  };

  const handleMouseUp = () => {
    // 完成框选
    if (isSelecting && selectionStart !== null && selectionEnd !== null) {
      const newStart = Math.min(selectionStart, selectionEnd);
      const newEnd = Math.max(selectionStart, selectionEnd);
      // 只有当框选区域足够大时才跳转（至少0.1秒）
      if (Math.abs(newEnd - newStart) > 0.1) {
        onViewportChange({ start: newStart, end: newEnd });
      }
      setIsSelecting(false);
      setSelectionStart(null);
      setSelectionEnd(null);
    }
    setIsDragging(false);
    setIsResizing(null);
  };

  useEffect(() => {
    if (isDragging || isResizing) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, isResizing, dragStartX, initialViewport]);

  const viewportLeftPercent = getLeftPercent(viewport.start);
  const viewportWidthPercent = ((viewport.end - viewport.start) / (dataMax - dataMin)) * 100;

  return (
    <div
      ref={containerRef}
      className="relative h-full bg-white overflow-hidden minimap-background"
      onMouseDown={handleContainerMouseDown}
    >
      {/* Background chart - reserve bottom axisHeight px for our internal x-axis */}
      <div
        ref={uplotContainerRef}
        className="absolute left-0 right-0 top-0 minimap-background"
        style={{ bottom: `${axisHeight}px` }}
      />

          {/* Annotation regions background (工业风格色块) */}
          <div className="absolute left-0 right-0 top-0 pointer-events-none" style={{ bottom: `${axisHeight}px` }}>
            {annotations.map((annotation) => {
              const leftPercent = getLeftPercent(annotation.startTime);
              const widthPercent = ((annotation.endTime - annotation.startTime) / (dataMax - dataMin)) * 100;
          
              return (
                <div
                  key={annotation.id}
                  className="absolute top-0"
                  style={{
                    left: `${leftPercent}%`,
                    width: `${widthPercent}%`,
                    height: `calc(100% )`,
                    backgroundColor: annotation.color,
                    opacity: 0.25,
                    overflow: 'hidden',
                  }}
                />
              );
            })}
          </div>

      {/* Dimmed areas outside viewport */}
      <div className="absolute left-0 right-0 top-0 pointer-events-none" style={{ bottom: `${axisHeight}px` }}>
        <div
          className="absolute top-0 left-0 bg-white/70"
          style={{ width: `${viewportLeftPercent}%`, bottom: 0 }}
        />
        <div
          className="absolute top-0 right-0 bg-white/70"
          style={{ width: `${100 - viewportLeftPercent - viewportWidthPercent}%`, bottom: 0 }}
        />
      </div>

      {/* Selection box (框选区域) */}
      {isSelecting && selectionStart !== null && selectionEnd !== null && (
        <div
          className="absolute top-0 pointer-events-none"
          style={{
            left: `${getLeftPercent(Math.min(selectionStart, selectionEnd))}%`,
            width: `${(Math.abs(selectionEnd - selectionStart) / (dataMax - dataMin)) * 100}%`,
            backgroundColor: 'rgba(24, 144, 255, 0.15)',
            border: '1px dashed #1890FF',
            bottom: `${axisHeight}px`,
          }}
        />
      )}

      {/* Viewport window */}
      <div
        className="absolute top-0 border border-[#1890FF] bg-transparent"
        style={{
          left: `${viewportLeftPercent}%`,
          width: `${viewportWidthPercent}%`,
          bottom: `${axisHeight}px`,
        }}
      >
        {/* Left handle (inside viewport) */}
        <div
          className="absolute top-0 left-0 w-2 bg-[#1890FF] cursor-ew-resize hover:bg-[#40a9ff] transition-colors"
          style={{ bottom: 0, height: '100%' }}
          onMouseDown={(e) => handleMouseDown(e, 'left')}
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-0.5 h-4 bg-white rounded" />
        </div>

        {/* Center drag area */}
        <div
          className="absolute top-0 left-0 right-0 cursor-grab active:cursor-grabbing"
          style={{ bottom: 0, height: '100%' }}
          onMouseDown={(e) => handleMouseDown(e, 'drag')}
        />

        {/* Right handle (inside viewport) */}
        <div
          className="absolute top-0 right-0 w-2 bg-[#1890FF] cursor-ew-resize hover:bg-[#40a9ff] transition-colors"
          style={{ bottom: 0, height: '100%' }}
          onMouseDown={(e) => handleMouseDown(e, 'right')}
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-0.5 h-4 bg-white rounded" />
        </div>
      </div>

      {/* x-axis hairline at top of axis area */}
        {/* axis hairline sits at the bottom of the axis band (under labels) */}
        <div
          className="absolute left-0 right-0"
          style={{ bottom: `0px`, height: '1px', backgroundColor: '#E0E0E0', zIndex: 0 }}
        />

      {/* Internal X-axis rendered inside the minimap box */}
        <div
          className="absolute left-0 right-0 bottom-0 h-5 flex items-center pointer-events-none"
          style={{ height: `${axisHeight}px`, zIndex: 10 }}
        >
          <div className="relative w-full">
            {/* ticks */}
            {Array.from({ length: 5 }).map((_, i) => {
              const t = dataMin + (i / 4) * (dataMax - dataMin);
              const left = getLeftPercent(t);
              return (
                <div
                  key={i}
                  className="absolute text-xs text-[#9E9E9E]"
                  style={{ left: `${left}%`, transform: 'translateX(-50%)', bottom: -8 }}
                >
                    {Math.round(t)}
                </div>
              );
            })}
          </div>
        </div>
    </div>
  );
}
