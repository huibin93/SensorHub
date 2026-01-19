import { useState, useCallback } from 'react';
import { X, Upload } from 'lucide-react';
import { Progress } from '@/app/components/ui/progress';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  deviceType: 'watch' | 'ring';
  onUploadComplete: (fileName: string) => void;
}

export function UploadModal({ isOpen, onClose, deviceType, onUploadComplete }: UploadModalProps) {
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    
    const files = Array.from(e.dataTransfer.files);
    const rawdataFile = files.find(f => f.name.endsWith('.rawdata'));
    
    if (rawdataFile) {
      handleUpload(rawdataFile);
    }
  }, []);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleUpload(file);
    }
  }, []);

  const handleUpload = (file: File) => {
    setIsUploading(true);
    setUploadProgress(0);

    // Simulate upload progress
    const interval = setInterval(() => {
      setUploadProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setTimeout(() => {
            onUploadComplete(file.name);
            onClose();
            setIsUploading(false);
            setUploadProgress(0);
          }, 300);
          return 100;
        }
        return prev + 10;
      });
    }, 200);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E4E7ED]">
          <h2 className="text-lg font-semibold text-[#2C3E50]">
            上传{deviceType === 'watch' ? '手表' : '指环'}数据
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-[#F5F7FA] rounded transition-colors"
          >
            <X className="w-5 h-5 text-[#909399]" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          <div
            className={`
              border-2 border-dashed rounded-lg p-12 text-center
              transition-colors duration-200
              ${isDragOver ? 'border-[#1890FF] bg-[#E6F7FF]' : 'border-[#E4E7ED] bg-[#FAFAFA]'}
              ${isUploading ? 'opacity-50 pointer-events-none' : 'cursor-pointer'}
            `}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => !isUploading && document.getElementById('file-input')?.click()}
          >
            <div className="flex flex-col items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-[#E6F7FF] flex items-center justify-center">
                <Upload className="w-8 h-8 text-[#1890FF]" />
              </div>
              <div>
                <div className="text-base font-medium text-[#2C3E50] mb-1">
                  拖拽文件到此处，或点击选择文件
                </div>
                <div className="text-sm text-[#909399]">
                  支持 .rawdata 格式
                </div>
              </div>
            </div>
            <input
              id="file-input"
              type="file"
              accept=".rawdata"
              className="hidden"
              onChange={handleFileSelect}
            />
          </div>

          {isUploading && (
            <div className="mt-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-[#2C3E50]">上传中...</span>
                <span className="text-sm text-[#909399]">{uploadProgress}%</span>
              </div>
              <Progress value={uploadProgress} className="h-2" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
