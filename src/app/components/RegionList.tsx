import { X, Trash2 } from 'lucide-react';
import { AnnotationRegion } from '@/app/types';
import { Button } from '@/app/components/ui/button';

interface RegionListProps {
  annotations: AnnotationRegion[];
  onDelete: (id: string) => void;
  onRegionClick: (region: AnnotationRegion) => void;
  onHoverChange: (id: string | null) => void;
  onClearAll: () => void;
  onRegionEdit?: (region: AnnotationRegion) => void;
}

export function RegionList({ 
  annotations, 
  onDelete, 
  onRegionClick, 
  onHoverChange, 
  onClearAll,
  onRegionEdit 
}: RegionListProps) {
  const formatTime = (seconds: number) => {
    return `${Math.round(seconds)}`;
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3 flex-shrink-0">
        <h3 className="text-sm font-semibold text-[#424242]">
          已标注区域 ({annotations.length})
        </h3>
        {annotations.length > 0 && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-[#D32F2F] hover:text-[#D32F2F] hover:bg-[#FFEBEE]"
            onClick={onClearAll}
          >
            <Trash2 className="w-3 h-3 mr-1" />
            清空
          </Button>
        )}
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto">
        {annotations.length === 0 ? (
          <div className="text-center py-8 text-sm text-[#9E9E9E]">
            暂无标注
          </div>
        ) : (
          annotations.map((annotation) => (
            <div
              key={annotation.id}
              className="bg-white rounded-lg p-3 border border-[#E4E7ED] cursor-pointer 
                       hover:border-[#1890FF] transition-all group"
              onClick={() => onRegionClick(annotation)}
              onMouseEnter={() => onHoverChange(annotation.id)}
              onMouseLeave={() => onHoverChange(null)}
            >
              <div className="flex items-start gap-3">
                {/* Color indicator */}
                <div
                  className="w-1 h-full rounded-full flex-shrink-0 mt-1"
                  style={{ backgroundColor: annotation.color, minHeight: '40px' }}
                />

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-[#2C3E50] mb-1">
                      {annotation.regionName ?? annotation.label}
                    </div>
                    <div className="text-xs text-[#909399]">
                      <span className="mr-2">{annotation.label}</span>
                      <span>{formatTime(annotation.startTime)} - {formatTime(annotation.endTime)}</span>
                    </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  {onRegionEdit && (
                    <button
                      className="p-1 hover:bg-[#E6F7FF] rounded"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRegionEdit(annotation);
                      }}
                      title="编辑"
                    >
                      <svg className="w-3 h-3 text-[#1890FF]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                    </button>
                  )}
                  <button
                    className="p-1 hover:bg-[#FEF0F0] rounded"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(annotation.id);
                    }}
                    title="删除"
                  >
                    <X className="w-3 h-3 text-[#F5222D]" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}