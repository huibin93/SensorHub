import { LabelType } from '@/app/types';
import { useEffect, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Button } from '@/app/components/ui/button';

interface LabelToolboxProps {
  labelTypes: LabelType[];
  selectedLabel: LabelType | null;
  onSelectLabel: (label: LabelType | null) => void;
  onAddLabel?: (label: LabelType) => void;
  onDeleteLabel?: (labelId: string) => void;
}

export function LabelToolbox({ labelTypes, selectedLabel, onSelectLabel, onAddLabel, onDeleteLabel }: LabelToolboxProps) {
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      const label = labelTypes.find((l) => l.shortcut === e.key);
      if (label) {
        // Toggle selection
        onSelectLabel(selectedLabel?.id === label.id ? null : label);
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [labelTypes, onSelectLabel, selectedLabel]);

  const handleAddLabel = () => {
    const colors = ['#FA541C', '#13C2C2', '#2F54EB', '#EB2F96', '#52C41A'];
    const newLabel: LabelType = {
      id: `custom-${Date.now()}`,
      name: `新标签${labelTypes.length + 1}`,
      color: colors[labelTypes.length % colors.length],
      shortcut: '',
    };
    onAddLabel?.(newLabel);
  };

  return (
    <div className="flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-[#2C3E50]">标签类型</h3>
        {onAddLabel && (
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-6 px-2"
            onClick={handleAddLabel}
          >
            <Plus className="w-3 h-3 mr-1" />
            添加
          </Button>
        )}
      </div>

      {/* Click outside to deselect */}
      <div 
        className="space-y-2 p-2 bg-white rounded-lg border border-[#E4E7ED] max-h-[300px] overflow-y-auto"
        onClick={(e) => {
          if (e.target === e.currentTarget) {
            onSelectLabel(null);
          }
        }}
      >
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-2 pb-2 border-b border-[#E4E7ED] text-xs font-medium text-[#909399]">
          <div className="col-span-1"></div>
          <div className="col-span-7">名称</div>
          <div className="col-span-2 text-center">快捷键</div>
          <div className="col-span-2"></div>
        </div>

        {/* Label Rows */}
        {labelTypes.map((label) => {
          const isSelected = selectedLabel?.id === label.id;
          return (
            <div
              key={label.id}
              className={`
                grid grid-cols-12 gap-2 items-center p-2 rounded cursor-pointer
                transition-all duration-150
                ${isSelected 
                  ? 'bg-[#E6F7FF] ring-2 ring-[#1890FF]' 
                  : 'hover:bg-[#FAFAFA]'
                }
              `}
              onClick={() => onSelectLabel(isSelected ? null : label)}
            >
              {/* Color indicator */}
              <div className="col-span-1">
                <div
                  className="w-4 h-4 rounded border-2"
                  style={{ 
                    backgroundColor: isSelected ? label.color : 'transparent',
                    borderColor: label.color 
                  }}
                />
              </div>

              {/* Name */}
              <div className="col-span-7">
                <span className="text-sm font-medium text-[#2C3E50]">
                  {label.name}
                </span>
              </div>

              {/* Shortcut */}
              <div className="col-span-2 text-center">
                {label.shortcut && (
                  <span className="inline-block px-2 py-0.5 bg-[#F5F7FA] text-xs font-mono rounded">
                    {label.shortcut}
                  </span>
                )}
              </div>

              {/* Delete */}
              <div className="col-span-2 text-right">
                {onDeleteLabel && labelTypes.length > 1 && (
                  <button
                    className="p-1 hover:bg-[#FEF0F0] rounded transition-colors"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteLabel(label.id);
                    }}
                  >
                    <Trash2 className="w-3 h-3 text-[#F5222D]" />
                  </button>
                )}
              </div>
            </div>
          );
        })}

        {labelTypes.length === 0 && (
          <div className="text-center py-4 text-xs text-[#909399]">
            暂无标签，点击上方"添加"创建标签
          </div>
        )}
      </div>

      <div className="mt-2 text-xs text-[#909399] text-center">
        提示：按数字键快速切换标签，点击空白处取消选择
      </div>
    </div>
  );
}