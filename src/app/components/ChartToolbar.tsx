import { Move, ZoomIn, Target, Edit3, Globe } from 'lucide-react';
import { useState } from 'react';

export type ToolMode = 'pan' | 'zoom' | 'annotate' | null;

interface ChartToolbarProps {
  activeMode: ToolMode;
  onModeChange: (mode: ToolMode) => void;
  onAutoAxis: () => void;
  onZoomOut: () => void;
  onOpenInBrowser?: () => void;
}

export function ChartToolbar({
  activeMode,
  onModeChange,
  onAutoAxis,
  onZoomOut,
  onOpenInBrowser,
}: ChartToolbarProps) {
  const tools = [
    { mode: 'pan' as ToolMode, icon: Move, label: '移动', description: '左键拖动平移' },
    { mode: 'zoom' as ToolMode, icon: ZoomIn, label: '放大', description: '左键框选放大，右键回退' },
    { mode: 'annotate' as ToolMode, icon: Edit3, label: '标注', description: '拖动创建标注' },
  ];

  return (
    <div className="flex items-center gap-2 p-2 bg-[#F5F7FA] rounded-lg border border-[#E4E7ED]">
      {/* Mode Toggles */}
      <div className="flex items-center gap-1 pr-2 border-r border-[#E4E7ED]">
        {tools.map((tool) => {
          const Icon = tool.icon;
          const isActive = activeMode === tool.mode;
          return (
            <button
              key={tool.mode}
              className={`
                group relative p-2 rounded transition-all
                ${isActive 
                  ? 'bg-[#1890FF] text-white' 
                  : 'hover:bg-white text-[#2C3E50]'
                }
              `}
              onClick={() => onModeChange(isActive ? null : tool.mode)}
              title={tool.label}
            >
              <Icon className="w-4 h-4" />
              
              {/* Tooltip */}
              <div className="absolute top-full left-1/2 -translate-x-1/2 mt-2 px-2 py-1 
                            bg-[#2C3E50] text-white text-xs rounded whitespace-nowrap
                            opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-10">
                {tool.label}: {tool.description}
              </div>
            </button>
          );
        })}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-1">
        <button
          className="px-3 py-1.5 text-xs font-medium text-[#2C3E50] hover:bg-white rounded transition-colors"
          onClick={onAutoAxis}
          title="查看全貌"
        >
          <Target className="w-4 h-4 inline mr-1" />
          查看全貌
        </button>
        {/* Open in browser icon */}
        <button
          className="p-2 rounded hover:bg-white transition-colors"
          onClick={() => onOpenInBrowser?.()}
          title="在新窗口打开"
        >
          <Globe className="w-4 h-4 text-[#2C3E50]" />
        </button>
      </div>
    </div>
  );
}
