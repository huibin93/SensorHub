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
  const uplotOptions = useMemo((): uPlot.Options => {
    return {
      width: dimensions.width,
      height: dimensions.height - 12,  // 为X轴标签预留较少空间，增加图表高度
      scales: {
        x: {
          time: false,
          range: [0, totalDuration],
        },
      },
      axes: [
        {
          show: true,
          stroke: '#BDBDBD',
          grid: { show: false },
          ticks: { stroke: '#BDBDBD', size: 4 },
          font: '10px sans-serif',
          labelSize: 16,
          gap: 2,
          values: (u, vals) => vals.map(v => `${v.toFixed(1)}s`),
        },
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
  }, [dimensions, totalDuration]);

  const { containerRef: uplotContainerRef } = useUplot(uplotData, uplotOptions, [totalDuration]);

  const getTimeFromPosition = (clientX: number): number => {
    if (!containerRef.current) return 0;
    const rect = containerRef.current.getBoundingClientRect();
    const ratio = (clientX - rect.left) / rect.width;
    return Math.max(0, Math.min(totalDuration, ratio * totalDuration));
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
    const deltaTime = (deltaX / rect.width) * totalDuration;

    if (isDragging) {
      const duration = viewport.end - viewport.start;
      let newStart = initialViewport.start + deltaTime;
      let newEnd = initialViewport.end + deltaTime;

      // Clamp to bounds
      if (newStart < 0) {
        newStart = 0;
        newEnd = duration;
      }
      if (newEnd > totalDuration) {
        newEnd = totalDuration;
        newStart = totalDuration - duration;
      }

      onViewportChange({ start: newStart, end: newEnd });
    } else if (isResizing === 'left') {
      const newStart = Math.max(0, Math.min(initialViewport.end - 1, initialViewport.start + deltaTime));
      onViewportChange({ start: newStart, end: viewport.end });
    } else if (isResizing === 'right') {
      const newEnd = Math.min(totalDuration, Math.max(initialViewport.start + 1, initialViewport.end + deltaTime));
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

  const viewportLeftPercent = (viewport.start / totalDuration) * 100;
  const viewportWidthPercent = ((viewport.end - viewport.start) / totalDuration) * 100;

  return (
    <div
      ref={containerRef}
      className="relative h-full bg-white overflow-hidden minimap-background"
      onMouseDown={handleContainerMouseDown}
    >
      {/* Background chart */}
      <div ref={uplotContainerRef} className="absolute inset-0 minimap-background" />

      {/* Annotation regions background (工业风格色块) */}
      <div className="absolute inset-0 pointer-events-none">
        {annotations.map((annotation) => {
          const leftPercent = (annotation.startTime / totalDuration) * 100;
          const widthPercent = ((annotation.endTime - annotation.startTime) / totalDuration) * 100;
          
          return (
            <div
              key={annotation.id}
              className="absolute top-0 bottom-0"
              style={{
                left: `${leftPercent}%`,
                width: `${widthPercent}%`,
                backgroundColor: annotation.color,
                opacity: 0.25,
              }}
            />
          );
        })}
      </div>

      {/* Dimmed areas outside viewport */}
      <div className="absolute inset-0 pointer-events-none">
        <div
          className="absolute top-0 bottom-0 left-0 bg-white/70"
          style={{ width: `${viewportLeftPercent}%` }}
        />
        <div
          className="absolute top-0 bottom-0 right-0 bg-white/70"
          style={{ width: `${100 - viewportLeftPercent - viewportWidthPercent}%` }}
        />
      </div>

      {/* Selection box (框选区域) */}
      {isSelecting && selectionStart !== null && selectionEnd !== null && (
        <div
          className="absolute top-0 bottom-0 pointer-events-none"
          style={{
            left: `${(Math.min(selectionStart, selectionEnd) / totalDuration) * 100}%`,
            width: `${(Math.abs(selectionEnd - selectionStart) / totalDuration) * 100}%`,
            backgroundColor: 'rgba(24, 144, 255, 0.2)',
            border: '2px dashed #1890FF',
          }}
        />
      )}

      {/* Viewport window */}
      <div
        className="absolute top-0 bottom-0 border border-[#1890FF] bg-transparent"
        style={{
          left: `${viewportLeftPercent}%`,
          width: `${viewportWidthPercent}%`,
        }}
      >
        {/* Left handle */}
        <div
          className="absolute top-0 bottom-0 -left-1 w-2 bg-[#1890FF] cursor-ew-resize hover:bg-[#40a9ff] transition-colors"
          onMouseDown={(e) => handleMouseDown(e, 'left')}
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-0.5 h-4 bg-white rounded" />
        </div>

        {/* Center drag area */}
        <div
          className="absolute inset-0 cursor-grab active:cursor-grabbing"
          onMouseDown={(e) => handleMouseDown(e, 'drag')}
        />

        {/* Right handle */}
        <div
          className="absolute top-0 bottom-0 -right-1 w-2 bg-[#1890FF] cursor-ew-resize hover:bg-[#40a9ff] transition-colors"
          onMouseDown={(e) => handleMouseDown(e, 'right')}
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-0.5 h-4 bg-white rounded" />
        </div>
      </div>
    </div>
  );
}
