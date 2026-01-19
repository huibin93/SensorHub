import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { AnnotationRegion, LabelType } from '@/app/types';
import { Button } from '@/app/components/ui/button';

interface AnnotationEditDialogProps {
  annotation: AnnotationRegion | null;
  labelTypes: LabelType[];
  onClose: () => void;
  onSave: (annotation: AnnotationRegion) => void;
}

export function AnnotationEditDialog({ 
  annotation, 
  labelTypes, 
  onClose, 
  onSave 
}: AnnotationEditDialogProps) {
  const [editedAnnotation, setEditedAnnotation] = useState<AnnotationRegion | null>(null);

  useEffect(() => {
    if (annotation) {
      setEditedAnnotation({ ...annotation });
    }
  }, [annotation]);

  if (!annotation || !editedAnnotation) return null;

  const handleSave = () => {
    onSave(editedAnnotation);
    onClose();
  };

  const selectedLabelType = labelTypes.find(l => l.name === editedAnnotation.label);

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      
      {/* Dialog */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-md mx-4">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E4E7ED]">
          <h2 className="text-lg font-semibold text-[#2C3E50]">编辑标注</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-[#F5F7FA] rounded transition-colors"
          >
            <X className="w-5 h-5 text-[#909399]" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Label Type Selection */}
          <div>
            <label className="block text-sm font-medium text-[#2C3E50] mb-2">
              标签类型
            </label>
            <div className="grid grid-cols-2 gap-2">
              {labelTypes.map((labelType) => {
                const isSelected = editedAnnotation.label === labelType.name;
                return (
                  <button
                    key={labelType.id}
                    className={`
                      p-3 rounded-lg border-2 text-sm font-medium transition-all
                      ${isSelected 
                        ? 'border-[#1890FF] bg-[#E6F7FF] text-[#1890FF]' 
                        : 'border-[#E4E7ED] hover:border-[#1890FF]'
                      }
                    `}
                    onClick={() => setEditedAnnotation({
                      ...editedAnnotation,
                      label: labelType.name,
                      color: labelType.color,
                    })}
                  >
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded"
                        style={{ backgroundColor: labelType.color }}
                      />
                      {labelType.name}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Time Range */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[#2C3E50] mb-2">
                开始时间 (秒)
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={editedAnnotation.startTime}
                onChange={(e) => setEditedAnnotation({
                  ...editedAnnotation,
                  startTime: Math.max(0, parseFloat(e.target.value) || 0),
                })}
                className="w-full px-3 py-2 border border-[#E4E7ED] rounded-lg 
                         focus:outline-none focus:ring-2 focus:ring-[#1890FF]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[#2C3E50] mb-2">
                结束时间 (秒)
              </label>
              <input
                type="number"
                step="0.1"
                min={editedAnnotation.startTime}
                value={editedAnnotation.endTime}
                onChange={(e) => setEditedAnnotation({
                  ...editedAnnotation,
                  endTime: Math.max(editedAnnotation.startTime, parseFloat(e.target.value) || 0),
                })}
                className="w-full px-3 py-2 border border-[#E4E7ED] rounded-lg 
                         focus:outline-none focus:ring-2 focus:ring-[#1890FF]"
              />
            </div>
          </div>

          {/* Duration Display */}
          <div className="text-sm text-[#909399]">
            时长: {(editedAnnotation.endTime - editedAnnotation.startTime).toFixed(1)}秒
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#E4E7ED]">
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button 
            className="bg-[#1890FF] hover:bg-[#1890FF]/90"
            onClick={handleSave}
          >
            保存
          </Button>
        </div>
      </div>
    </div>
  );
}
