import { useRef, useState, useEffect } from 'react';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import { TimeSeriesDataPoint } from '@/app/types';

interface MiniMapProps {
  data: TimeSeriesDataPoint[];
  totalDuration: number;
  viewport: { start: number; end: number };
  onViewportChange: (viewport: { start: number; end: number }) => void;
}

export function MiniMap({ data, totalDuration, viewport, onViewportChange }: MiniMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState<'left' | 'right' | null>(null);
  const [dragStartX, setDragStartX] = useState(0);
  const [initialViewport, setInitialViewport] = useState(viewport);

  // Downsample data for minimap
  const downsampledData = data.filter((_, i) => i % 10 === 0);

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

  const handleMouseMove = (e: MouseEvent) => {
    if (!containerRef.current) return;

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
      className="relative h-full bg-white rounded-lg border border-[#E4E7ED] overflow-hidden"
    >
      {/* Background chart */}
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={downsampledData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
          <Line
            type="monotone"
            dataKey="accX"
            stroke="#909399"
            strokeWidth={1}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>

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

      {/* Viewport window */}
      <div
        className="absolute top-0 bottom-0 border-2 border-[#1890FF] bg-transparent"
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
