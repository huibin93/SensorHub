import { useRef, useEffect } from 'react';
import { AnnotationRegion } from '../types';
import { useRegions } from '../hooks/useRegions';

interface OverlayCanvasProps {
  width: number;
  height: number;
  annotations: AnnotationRegion[];
  viewport: { start: number; end: number };
  hoveredRegionId: string | null;
  selectedRegionId?: string | null;
  dragSelection?: { start: number; end: number; color: string } | null;
  mousePosition?: { x: number; time: number } | null;
  // nearest point info computed by chart: { idx, time, points: [{series, value, x, y, color}] }
  nearestInfo?: { idx: number; time: number; points: { series: string; value: number; x: number; y: number; color: string }[] } | null;
  onMouseDown?: (e: React.MouseEvent<HTMLCanvasElement>) => void;
  onMouseMove?: (e: React.MouseEvent<HTMLCanvasElement>) => void;
  onMouseUp?: (e: React.MouseEvent<HTMLCanvasElement>) => void;
  onMouseLeave?: () => void;
  cursor?: string;
  showVerticalLines?: boolean;  // 新增：是否显示垂直辅助线
}

export function OverlayCanvas({
  width,
  height,
  annotations,
  viewport,
  hoveredRegionId,
  selectedRegionId,
  dragSelection,
  mousePosition,
  nearestInfo,
  onMouseDown,
  onMouseMove,
  onMouseUp,
  onMouseLeave,
  cursor = 'default',
  showVerticalLines = false,
}: OverlayCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { timeToPixel } = useRegions();

  // Helper function to add opacity to color
  const addOpacity = (color: string, opacity: number): string => {
    // Handle hex colors
    if (color.startsWith('#')) {
      const hex = color.replace('#', '');
      const r = parseInt(hex.substring(0, 2), 16);
      const g = parseInt(hex.substring(2, 4), 16);
      const b = parseInt(hex.substring(4, 6), 16);
      return `rgba(${r}, ${g}, ${b}, ${opacity})`;
    }
    // Handle rgb colors
    if (color.startsWith('rgb(')) {
      return color.replace('rgb(', 'rgba(').replace(')', `, ${opacity})`);
    }
    // Handle rgba colors - replace existing alpha
    if (color.startsWith('rgba(')) {
      return color.replace(/,[\s]*[\d.]+\)/, `, ${opacity})`);
    }
    // Fallback
    return color;
  };

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) return;

    // DPR 适配（Label Studio 风格）
    const dpr = window.devicePixelRatio || 1;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    ctx.scale(dpr, dpr);

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Draw vertical grid lines (工业风格垂直辅助线)
    if (showVerticalLines) {
      const duration = viewport.end - viewport.start;
      const interval = Math.pow(10, Math.floor(Math.log10(duration))) / 2;
      const startTime = Math.floor(viewport.start / interval) * interval;
      
      ctx.strokeStyle = '#E0E0E0';
      ctx.lineWidth = 1;
      ctx.setLineDash([]);
      
      // 使用 0.5 像素偏移以获得更清晰的线条
      ctx.beginPath();
      for (let time = startTime; time <= viewport.end; time += interval) {
        if (time >= viewport.start) {
          const x = Math.floor(timeToPixel(time, viewport.start, viewport.end, width)) + 0.5;
          ctx.moveTo(x, 0);
          ctx.lineTo(x, height);
        }
      }
      ctx.stroke();
    }

    // Draw annotations
    annotations.forEach((annotation) => {
      // Skip if outside viewport
      if (annotation.endTime < viewport.start || annotation.startTime > viewport.end) {
        return;
      }

      const startX = timeToPixel(annotation.startTime, viewport.start, viewport.end, width);
      const endX = timeToPixel(annotation.endTime, viewport.start, viewport.end, width);
      const regionWidth = endX - startX;

      const isHovered = annotation.id === hoveredRegionId;
      const isSelected = selectedRegionId ? annotation.id === selectedRegionId : false;

      // Parse color and add opacity (Label Studio 风格)
      const color = annotation.color;
      const fillOpacity = isHovered ? 0.25 : 0.18;
      const borderOpacity = isHovered ? 0.8 : 0.6;
      
      // Draw region background (半透明色块)
      ctx.fillStyle = addOpacity(color, fillOpacity);
      ctx.fillRect(startX, 0, regionWidth, height);

      // Draw top border (顶部边框)
      ctx.strokeStyle = addOpacity(color, borderOpacity);
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(startX, 0);
      ctx.lineTo(endX, 0);
      ctx.stroke();

      // Draw vertical borders (垂直边框)
      ctx.strokeStyle = addOpacity(color, borderOpacity * 0.6);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(startX, 0);
      ctx.lineTo(startX, height);
      ctx.moveTo(endX, 0);
      ctx.lineTo(endX, height);
      ctx.stroke();

      // Draw center handle (中间抓手)
      const centerX = (startX + endX) / 2;
      const handleWidth = 8;
      const handleHeight = 16;
      ctx.fillStyle = isHovered ? addOpacity(color, 0.8) : addOpacity(color, 0.5);
      ctx.fillRect(centerX - handleWidth / 2, 2, handleWidth, handleHeight);
      
      // Handle border
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      ctx.strokeRect(centerX - handleWidth / 2, 2, handleWidth, handleHeight);

      // Draw edge handles (边缘调整手柄)
      // Show when hovered OR when explicitly selected
      if (isHovered || isSelected) {
        const edgeHandleWidth = 4;
        const edgeHandleHeight = 30;
        const edgeHandleY = height / 2 - edgeHandleHeight / 2;

        // Left edge handle
        ctx.fillStyle = addOpacity(color, 0.8);
        ctx.fillRect(startX - edgeHandleWidth / 2, edgeHandleY, edgeHandleWidth, edgeHandleHeight);
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.strokeRect(startX - edgeHandleWidth / 2, edgeHandleY, edgeHandleWidth, edgeHandleHeight);

        // Right edge handle
        ctx.fillRect(endX - edgeHandleWidth / 2, edgeHandleY, edgeHandleWidth, edgeHandleHeight);
        ctx.strokeRect(endX - edgeHandleWidth / 2, edgeHandleY, edgeHandleWidth, edgeHandleHeight);
      }

      // Draw label if hovered
      if (isHovered && annotation.label) {
        const labelX = startX + 5;
        const labelY = 20;
        
        ctx.font = '12px sans-serif';
        const textMetrics = ctx.measureText(annotation.label);
        const textWidth = textMetrics.width;
        
        // Draw label background
        ctx.fillStyle = 'rgba(44, 62, 80, 0.9)';
        ctx.fillRect(labelX - 2, labelY - 14, textWidth + 4, 18);
        
        // Draw label text
        ctx.fillStyle = '#ffffff';
        ctx.fillText(annotation.label, labelX, labelY);
      }
    });

    // Draw drag selection
    if (dragSelection) {
      const startX = timeToPixel(dragSelection.start, viewport.start, viewport.end, width);
      const endX = timeToPixel(dragSelection.end, viewport.start, viewport.end, width);
      const regionWidth = Math.abs(endX - startX);
      const minX = Math.min(startX, endX);

      // Draw selection background
      const color = dragSelection.color;
      ctx.fillStyle = addOpacity(color, 0.15); // 降低透明度
      ctx.fillRect(minX, 0, regionWidth, height);

      // Draw selection borders
      ctx.strokeStyle = addOpacity(color, 0.6); // 降低边框不透明度
      ctx.lineWidth = 2;
      ctx.strokeRect(minX, 0, regionWidth, height);
    }

    // Draw vertical crosshair (垂直参考线)
    if (mousePosition) {
      const rawX = mousePosition.x;
      // clamp draw position into canvas bounds
      const drawX = Math.max(0, Math.min(width, rawX));

      // If rawX is outside bounds, draw a faded indicator at the edge
      const isClamped = rawX < 0 || rawX > width;

      ctx.strokeStyle = isClamped ? 'rgba(66,66,66,0.25)' : '#424242';
      ctx.lineWidth = 1;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(drawX + 0.5, 0);
      ctx.lineTo(drawX + 0.5, height);
      ctx.stroke();
      ctx.setLineDash([]);

      if (isClamped) {
        // small triangle indicator to show direction
        ctx.fillStyle = 'rgba(66,66,66,0.25)';
        const size = 6;
        if (rawX < 0) {
          ctx.beginPath();
          ctx.moveTo(2, height / 2 - size);
          ctx.lineTo(2, height / 2 + size);
          ctx.lineTo(2 + size, height / 2);
          ctx.closePath();
          ctx.fill();
        } else {
          ctx.beginPath();
          ctx.moveTo(width - 2, height / 2 - size);
          ctx.lineTo(width - 2, height / 2 + size);
          ctx.lineTo(width - 2 - size, height / 2);
          ctx.closePath();
          ctx.fill();
        }
      }

      // Draw nearest-point markers + tooltip if provided
      if ((nearestInfo as any)?.points) {
        const info = nearestInfo as any;
        // Draw markers
        for (const p of info.points) {
          if (typeof p.y !== 'number' || Number.isNaN(p.y)) continue;
          ctx.beginPath();
          ctx.fillStyle = p.color || '#000';
          ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
          ctx.fill();
          ctx.lineWidth = 1;
          ctx.strokeStyle = '#fff';
          ctx.stroke();
        }

        // Prepare lines: time + per-series
        ctx.font = '12px sans-serif';
        const timeText = `T   +${info.time.toFixed(1)}s`;
        const lines = [timeText, ...info.points.map((p: any) => `${p.series}: ${p.value.toFixed(2)}`)];

        // Measure and compute box size with a smaller minimum width
        const padding = 6;
        const lineHeight = 16;
        const minWidth = 64;
        const maxWidth = Math.max(...lines.map((l: string) => ctx.measureText(l).width));
        const boxW = Math.max(minWidth, maxWidth + padding * 2);
        const boxH = lines.length * lineHeight + 6;

        // Position tooltip so it stays inside canvas
        const tooltipY = 6;
        const tooltipX = Math.max(8, Math.min(width - boxW - 8, mousePosition.x));

        // Background
        ctx.fillStyle = 'rgba(44,62,80,0.95)';
        ctx.fillRect(tooltipX, tooltipY, boxW, boxH);

        // Draw lines
        ctx.fillStyle = '#fff';
        for (let i = 0; i < lines.length; i++) {
          const txt = lines[i];
          const lx = tooltipX + padding;
          const ly = tooltipY + padding + 12 + i * lineHeight;
          // colored dot for series lines (skip first time line)
          if (i > 0) {
            const color = info.points[i - 1].color || '#000';
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(tooltipX + 8, ly - 6, 4, 0, Math.PI * 2);
            ctx.fill();
            ctx.fillStyle = '#fff';
            ctx.fillText(txt, lx + 14, ly);
          } else {
            ctx.fillText(txt, lx, ly);
          }
        }
      }
    }
  }, [width, height, annotations, viewport, hoveredRegionId, dragSelection, mousePosition, timeToPixel, nearestInfo]);


  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        cursor,
        pointerEvents: 'all',
      }}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onMouseLeave={onMouseLeave}
    />
  );
}
