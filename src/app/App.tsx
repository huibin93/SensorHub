import { useState, useEffect } from 'react';
import { DataDashboard } from './components/DataDashboard';
import { UploadModal } from './components/UploadModal';
import { AnnotatorDrawer } from './components/AnnotatorDrawer';
import { mockDataFiles, generateMockTimeSeriesData, labelTypes } from './mockData';
import { DataFile, FileDetail } from './types';
import { Toaster, toast } from 'sonner';

export default function App() {
  const [dataFiles, setDataFiles] = useState<DataFile[]>(mockDataFiles);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [uploadDeviceType, setUploadDeviceType] = useState<'watch' | 'ring'>('watch');
  const [selectedFileDetail, setSelectedFileDetail] = useState<FileDetail | null>(null);
  const [newlyAddedFileId, setNewlyAddedFileId] = useState<string | null>(null);

  // Clear highlight after animation
  useEffect(() => {
    if (newlyAddedFileId) {
      const timer = setTimeout(() => setNewlyAddedFileId(null), 2000);
      return () => clearTimeout(timer);
    }
  }, [newlyAddedFileId]);

  const handleUploadClick = (deviceType: 'watch' | 'ring') => {
    setUploadDeviceType(deviceType);
    setUploadModalOpen(true);
  };

  const handleUploadComplete = (fileName: string) => {
    const newFile: DataFile = {
      id: Date.now().toString(),
      fileName,
      deviceType: uploadDeviceType,
      collectionTime: new Date().toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      }),
      dataSize: `${(Math.random() * 40 + 10).toFixed(1)} MB`,
      parseStatus: 'parsing',
      parseProgress: 0,
    };

    setDataFiles((prev) => [newFile, ...prev]);
    setNewlyAddedFileId(newFile.id);

    // Simulate parsing progress
    let progress = 0;
    const interval = setInterval(() => {
      progress += 15;
      if (progress >= 100) {
        clearInterval(interval);
        setDataFiles((prev) =>
          prev.map((f) =>
            f.id === newFile.id
              ? {
                  ...f,
                  parseStatus: 'completed',
                  parseProgress: 100,
                  metadata: {
                    serialNumber: `SN${Math.random().toString(36).substr(2, 8).toUpperCase()}`,
                    sampleRate: 50,
                  },
                }
              : f
          )
        );
        toast.success('文件解析完成！');
      } else {
        setDataFiles((prev) =>
          prev.map((f) => (f.id === newFile.id ? { ...f, parseProgress: progress } : f))
        );
      }
    }, 400);
  };

  const handleFileClick = (fileId: string) => {
    const file = dataFiles.find((f) => f.id === fileId);
    if (file && file.parseStatus === 'completed') {
      const mockData = generateMockTimeSeriesData(135);
      const detail: FileDetail = {
        file,
        data: mockData,
        totalDuration: 135,
        annotations: [
          {
            id: '1',
            label: 'Walking',
            startTime: 10,
            endTime: 45,
            color: '#52C41A',
          },
          {
            id: '2',
            label: 'Running',
            startTime: 50,
            endTime: 85,
            color: '#F5222D',
          },
        ],
      };
      setSelectedFileDetail(detail);
    }
  };

  const handleDeleteFile = (fileId: string) => {
    if (confirm('确定要删除这个文件吗？')) {
      setDataFiles((prev) => prev.filter((f) => f.id !== fileId));
      toast.success('文件已删除');
    }
  };

  const handleCloseDrawer = () => {
    setSelectedFileDetail(null);
  };

  return (
    <div className="min-h-screen bg-white">
      <DataDashboard
        dataFiles={dataFiles}
        onFileClick={handleFileClick}
        onUploadClick={handleUploadClick}
        onDeleteClick={handleDeleteFile}
        newlyAddedFileId={newlyAddedFileId}
      />

      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        deviceType={uploadDeviceType}
        onUploadComplete={handleUploadComplete}
      />

      {selectedFileDetail && (
        <AnnotatorDrawer
          fileDetail={selectedFileDetail}
          onClose={handleCloseDrawer}
          labelTypes={labelTypes}
        />
      )}

      <Toaster position="top-right" />
    </div>
  );
}