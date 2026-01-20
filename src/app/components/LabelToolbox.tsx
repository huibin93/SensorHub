import { LabelType, AnnotationRegion } from '@/app/types';
import { Plus, Trash2, CheckSquare, Square, MinusSquare } from 'lucide-react';
import { Button } from '@/app/components/ui/button';

interface LabelToolboxProps {
  labelTypes: LabelType[];
  selectedLabels: LabelType[];
  annotations: AnnotationRegion[];
  onSelectLabels: (labels: LabelType[]) => void;
  onAddLabel?: (label: LabelType) => void;
  onDeleteLabel?: (labelId: string) => void;
}

export function LabelToolbox({ labelTypes, selectedLabels, annotations, onSelectLabels, onAddLabel, onDeleteLabel }: LabelToolboxProps) {
  const handleAddLabel = () => {
    const colors = ['#FA541C', '#13C2C2', '#2F54EB', '#EB2F96', '#52C41A'];
    // Generate English-only label name following `label_XXX` pattern
    const nextIndex = labelTypes.length + 1;
    const generatedName = `label_${String(nextIndex).padStart(3, '0')}`;
    const newLabel: LabelType = {
      id: `label-${String(nextIndex).padStart(3, '0')}`,
      name: generatedName,
      color: colors[labelTypes.length % colors.length],
      shortcut: '',
    };
    onAddLabel?.(newLabel);
  };

  // Checkbox toggle: multi-select behavior (stopPropagation to avoid row click)
  const handleCheckboxToggle = (e: React.MouseEvent, label: LabelType) => {
    e.stopPropagation();
    const isSelected = selectedLabels.some(l => l.id === label.id);
    if (isSelected) {
      onSelectLabels(selectedLabels.filter(l => l.id !== label.id));
    } else {
      onSelectLabels([...selectedLabels, label]);
    }
  };

  // Row click: single-select this label (replace selection)
  const handleRowClick = (label: LabelType) => {
    onSelectLabels([label]);
  };

  // 统计每个标签的使用次数
  const getLabelCount = (labelName: string) => {
    return annotations.filter(a => a.label === labelName).length;
  };

  // 计算三态状态
  const allSelected = selectedLabels.length === labelTypes.length && labelTypes.length > 0;
  const someSelected = selectedLabels.length > 0 && selectedLabels.length < labelTypes.length;
  const noneSelected = selectedLabels.length === 0;

  // 三态选框点击逻辑：未选中/半选中 -> 全选，全选 -> 清空
  const handleToggleSelection = () => {
    if (allSelected) {
      onSelectLabels([]);
    } else {
      onSelectLabels([...labelTypes]);
    }
  };

  // 单个标签点击切换
  const handleLabelClick = (label: LabelType) => {
    const isSelected = selectedLabels.some(l => l.id === label.id);
    if (isSelected) {
      onSelectLabels(selectedLabels.filter(l => l.id !== label.id));
    } else {
      onSelectLabels([...selectedLabels, label]);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h3 className="text-sm font-semibold text-[#2C3E50]">标签类型</h3>
        <div className="flex gap-1">
          <Button 
            variant="ghost" 
            size="sm" 
            className="h-6 w-6 p-0"
            onClick={handleToggleSelection}
            title={allSelected ? "清空" : "全选"}
          >
            {allSelected ? (
              <CheckSquare className="w-3.5 h-3.5" />
            ) : someSelected ? (
              <MinusSquare className="w-3.5 h-3.5" />
            ) : (
              <Square className="w-3.5 h-3.5" />
            )}
          </Button>
          {onAddLabel && (
            <Button 
              variant="ghost" 
              size="sm" 
              className="h-6 w-6 p-0"
              onClick={handleAddLabel}
              title="添加标签"
            >
              <Plus className="w-3.5 h-3.5" />
            </Button>
          )}
        </div>
      </div>

      <div 
        className="flex-1 space-y-2 p-2 bg-white rounded-lg border border-[#E4E7ED] overflow-y-auto"
      >
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-2 pb-2 border-b border-[#E4E7ED] text-xs font-medium text-[#909399]">
          <div className="col-span-1"></div>
          <div className="col-span-7">名称</div>
          <div className="col-span-2 text-center">区域数</div>
          <div className="col-span-2"></div>
        </div>

        {/* Label Rows */}
        {labelTypes.map((label) => {
          const isSelected = selectedLabels.some(l => l.id === label.id);
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
              onClick={() => handleRowClick(label)}
            >
              {/* Checkbox for multi-select */}
              <div className="col-span-1 flex items-center">
                <input
                  type="checkbox"
                  checked={isSelected}
                  onClick={(e) => handleCheckboxToggle(e as any, label)}
                  onChange={() => { /* handled in onClick to control propagation */ }}
                />
              </div>

              {/* Name */}
              <div className="col-span-7">
                <span className="text-sm font-medium text-[#2C3E50]">
                  {label.name}
                </span>
              </div>

              {/* Count */}
              <div className="col-span-2 text-center">
                <span className="inline-block px-2 py-0.5 bg-[#F5F7FA] text-xs rounded font-medium text-[#606266]">
                  {getLabelCount(label.name)}
                </span>
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

    </div>
  );
}