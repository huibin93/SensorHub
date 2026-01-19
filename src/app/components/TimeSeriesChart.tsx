import { useState, useRef, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer, ReferenceArea } from 'recharts';
import { TimeSeriesDataPoint, AnnotationRegion, LabelType } from '@/app/types';
import { ToolMode } from './ChartToolbar';

interface TimeSeriesChartProps {
  data: TimeSeriesDataPoint[];
  viewport: { start: number; end: number };
  channel: 'acc' | 'gyro';
  annotations: AnnotationRegion[];
  selectedLabel: LabelType | null;
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
  selectedLabel,
  onCreateAnnotation,
  hoveredRegionId,
  toolMode,
  onViewportChange,
  yAxisDomain,
}: TimeSeriesChartProps) {
  const [mousePosition, setMousePosition] = useState<number | null>(null);
  const [dragStart, setDragStart] = useState<number | null>(null);
  const [dragEnd, setDragEnd] = useState<number | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [panStartX, setPanStartX] = useState<number | null>(null);
  const [panStartViewport, setPanStartViewport] = useState(viewport);
  const chartRef = useRef<HTMLDivElement>(null);

  // Filter data for viewport
  const filteredData = data.filter(
    (d) => d.time >= viewport.start && d.time <= viewport.end
  );

  // Colors for channels
  const colors = {
    acc: {
      x: '#F5222D',
      y: '#52C41A',
      z: '#1890FF',
    },
    gyro: {
      x: '#FA8C16',
      y: '#722ED1',
      z: '#13C2C2',
    },
  };

  const handleMouseMove = (e: any) => {
    if (e && e.activeLabel !== undefined) {
      const time = parseFloat(e.activeLabel);
      setMousePosition(time);
      
      // Update tooltip position
      if (chartRef.current && e.chartX !== undefined && e.chartY !== undefined) {
        setTooltipPosition({ x: e.chartX, y: e.chartY });
      }
      
      // Handle different tool modes
      if (toolMode === 'annotate' && dragStart !== null) {
        setDragEnd(time);
      } else if (toolMode === 'zoom' && dragStart !== null) {
        setDragEnd(time);
      }
    }
  };

  const handleMouseDown = (e: any) => {
    if (!e || e.activeLabel === undefined) return;
    
    const time = parseFloat(e.activeLabel);
    
    if (toolMode === 'annotate') {
      setDragStart(time);
      setDragEnd(time);
    } else if (toolMode === 'zoom') {
      setDragStart(time);
      setDragEnd(time);
    } else if (toolMode === 'pan' && e.chartX !== undefined) {
      setPanStartX(e.chartX);
      setPanStartViewport(viewport);
    }
  };

  const handleMouseUp = (e: any) => {
    if (toolMode === 'annotate' && dragStart !== null && dragEnd !== null) {
      if (Math.abs(dragEnd - dragStart) > 0.5) {
        onCreateAnnotation(dragStart, dragEnd);
      }
      setDragStart(null);
      setDragEnd(null);
    } else if (toolMode === 'zoom' && dragStart !== null && dragEnd !== null) {
      if (Math.abs(dragEnd - dragStart) > 0.5) {
        const newStart = Math.min(dragStart, dragEnd);
        const newEnd = Math.max(dragStart, dragEnd);
        onViewportChange?.({ start: newStart, end: newEnd });
      }
      setDragStart(null);
      setDragEnd(null);
    } else if (toolMode === 'pan') {
      setPanStartX(null);
    }
  };

  const handleMouseLeave = () => {
    setMousePosition(null);
    setDragStart(null);
    setDragEnd(null);
    setPanStartX(null);
  };

  // Handle pan movement
  const handleChartMouseMove = (e: React.MouseEvent) => {
    if (toolMode === 'pan' && panStartX !== null && chartRef.current) {
      const rect = chartRef.current.getBoundingClientRect();
      const deltaX = e.clientX - panStartX - rect.left;
      const deltaTime = -(deltaX / rect.width) * (viewport.end - viewport.start);
      
      const duration = panStartViewport.end - panStartViewport.start;
      let newStart = panStartViewport.start + deltaTime;
      let newEnd = panStartViewport.end + deltaTime;
      
      // Find min and max time in data
      const minTime = Math.min(...data.map(d => d.time));
      const maxTime = Math.max(...data.map(d => d.time));
      
      // Clamp to bounds
      if (newStart < minTime) {
        newStart = minTime;
        newEnd = minTime + duration;
      }
      if (newEnd > maxTime) {
        newEnd = maxTime;
        newStart = maxTime - duration;
      }
      
      onViewportChange?.({ start: newStart, end: newEnd });
    }
  };

  // Right click to zoom out (for zoom tool)
  const handleContextMenu = (e: React.MouseEvent) => {
    if (toolMode === 'zoom') {
      e.preventDefault();
      // Zoom out by 50%
      const duration = viewport.end - viewport.start;
      const center = (viewport.start + viewport.end) / 2;
      const newDuration = duration * 1.5;
      
      const minTime = Math.min(...data.map(d => d.time));
      const maxTime = Math.max(...data.map(d => d.time));
      
      let newStart = center - newDuration / 2;
      let newEnd = center + newDuration / 2;
      
      newStart = Math.max(minTime, newStart);
      newEnd = Math.min(maxTime, newEnd);
      
      onViewportChange?.({ start: newStart, end: newEnd });
    }
  };

  // Get cursor style based on tool mode
  const getCursorStyle = () => {
    if (toolMode === 'pan') return 'grab';
    if (toolMode === 'zoom') return 'crosshair';
    if (toolMode === 'annotate') return 'cell';
    return 'default';
  };

  // Filter annotations for current viewport
  const visibleAnnotations = annotations.filter(
    (a) => a.endTime >= viewport.start && a.startTime <= viewport.end
  );

  return (
    <div
      ref={chartRef}
      className="relative bg-white rounded-lg border border-[#E4E7ED] p-4 h-[300px]"
      onMouseUp={handleMouseUp}
      onMouseMove={handleChartMouseMove}
      onContextMenu={handleContextMenu}
      style={{ cursor: getCursorStyle() }}
    >
      <div className="mb-2">
        <h3 className="text-sm font-medium text-[#2C3E50]">
          {channel === 'acc' ? 'Accelerometer (ACC)' : 'Gyroscope (GYRO)'}
        </h3>
      </div>
      <ResponsiveContainer width="100%" height="90%">
        <LineChart
          data={filteredData}
          margin={{ top: 5, right: 5, left: 5, bottom: 5 }}
          onMouseMove={handleMouseMove}
          onMouseDown={handleMouseDown}
          onMouseLeave={handleMouseLeave}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#E4E7ED" />
          <XAxis
            dataKey="time"
            type="number"
            domain={[viewport.start, viewport.end]}
            tickFormatter={(val) => `${val.toFixed(1)}s`}
            stroke="#909399"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            stroke="#909399" 
            style={{ fontSize: '12px' }}
            domain={yAxisDomain || ['auto', 'auto']}
          />

          {/* Annotation regions */}
          {visibleAnnotations.map((annotation) => (
            <ReferenceArea
              key={annotation.id}
              x1={annotation.startTime}
              x2={annotation.endTime}
              fill={annotation.color}
              fillOpacity={hoveredRegionId === annotation.id ? 0.25 : 0.1}
              stroke={annotation.color}
              strokeWidth={hoveredRegionId === annotation.id ? 2 : 1}
              strokeOpacity={0.5}
            />
          ))}

          {/* Current drag selection */}
          {dragStart !== null && dragEnd !== null && (
            <ReferenceArea
              x1={dragStart}
              x2={dragEnd}
              fill={toolMode === 'zoom' ? '#909399' : (selectedLabel?.color || '#1890FF')}
              fillOpacity={0.2}
              stroke={toolMode === 'zoom' ? '#909399' : (selectedLabel?.color || '#1890FF')}
              strokeWidth={2}
            />
          )}

          <Line
            type="monotone"
            dataKey={channel === 'acc' ? 'accX' : 'gyroX'}
            stroke={colors[channel].x}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey={channel === 'acc' ? 'accY' : 'gyroY'}
            stroke={colors[channel].y}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
          <Line
            type="monotone"
            dataKey={channel === 'acc' ? 'accZ' : 'gyroZ'}
            stroke={colors[channel].z}
            strokeWidth={1.5}
            dot={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Time tooltip */}
      {mousePosition !== null && tooltipPosition.x > 0 && (
        <div
          className="absolute bg-[#2C3E50] text-white text-xs px-2 py-1 rounded pointer-events-none z-10"
          style={{
            left: `${tooltipPosition.x}px`,
            top: '40px',
          }}
        >
          T+{mousePosition.toFixed(1)}s
        </div>
      )}
    </div>
  );
}
