import { Watch, Loader2, CheckCircle2, XCircle, Trash2, Download, Upload } from 'lucide-react';
import { DataFile } from '@/app/types';
import { Button } from '@/app/components/ui/button';

interface DataDashboardProps {
  dataFiles: DataFile[];
  onFileClick: (fileId: string) => void;
  onUploadClick: (deviceType: 'watch' | 'ring') => void;
  onDeleteClick: (fileId: string) => void;
  newlyAddedFileId?: string | null;
}

export function DataDashboard({ dataFiles, onFileClick, onUploadClick, onDeleteClick, newlyAddedFileId }: DataDashboardProps) {
  const getStatusIcon = (status: DataFile['parseStatus'], progress?: number) => {
    switch (status) {
      case 'parsing':
        return (
          <div className="flex items-center gap-2 text-[#1890FF]">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span className="text-sm">{progress}%</span>
          </div>
        );
      case 'completed':
        return (
          <div className="flex items-center gap-2 text-[#52C41A]">
            <CheckCircle2 className="w-4 h-4" />
            <span className="text-sm">完成</span>
          </div>
        );
      case 'failed':
        return (
          <div className="flex items-center gap-2 text-[#F5222D]">
            <XCircle className="w-4 h-4" />
            <span className="text-sm">失败</span>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-white">
      {/* Navbar */}
      <nav className="h-16 border-b border-[#E4E7ED] px-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#1890FF] rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">SHb</span>
          </div>
          <h1 className="text-xl font-semibold text-[#2C3E50]">时序数据标注平台</h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-[#F5F7FA] rounded-full flex items-center justify-center">
            <span className="text-sm text-[#2C3E50]">U</span>
          </div>
        </div>
      </nav>

      {/* Hero Section - Upload Buttons */}
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid grid-cols-2 gap-6 mb-12">
          <button
            onClick={() => onUploadClick('watch')}
            className="group h-[120px] bg-white border-2 border-[#1890FF] rounded-xl 
                     flex items-center gap-6 px-8 hover:shadow-lg hover:-translate-y-0.5 
                     transition-all duration-200"
          >
            <div className="w-16 h-16 rounded-full bg-[#E6F7FF] flex items-center justify-center 
                          group-hover:scale-110 transition-transform duration-200">
              <Watch className="w-8 h-8 text-[#1890FF]" />
            </div>
            <div className="text-left">
              <div className="text-lg font-medium text-[#2C3E50] mb-1">手表数据</div>
              <div className="text-sm text-[#909399]">上传手表原始数据 (.rawdata)</div>
            </div>
          </button>

          <button
            onClick={() => onUploadClick('ring')}
            className="group h-[120px] bg-white border-2 border-[#722ED1] rounded-xl 
                     flex items-center gap-6 px-8 hover:shadow-lg hover:-translate-y-0.5 
                     transition-all duration-200"
          >
            <div className="w-16 h-16 rounded-full bg-[#F3E5FF] flex items-center justify-center
                          group-hover:scale-110 transition-transform duration-200">
              <div className="w-8 h-8 rounded-full border-4 border-[#722ED1]" />
            </div>
            <div className="text-left">
              <div className="text-lg font-medium text-[#2C3E50] mb-1">指环数据</div>
              <div className="text-sm text-[#909399]">上传指环原始数据 (.rawdata)</div>
            </div>
          </button>
        </div>

        {/* Data Table */}
        <div className="bg-[#F5F7FA] rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-white border-b border-[#E4E7ED]">
              <tr>
                <th className="px-6 py-4 text-left text-sm font-medium text-[#2C3E50]">文件名</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-[#2C3E50]">设备类型</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-[#2C3E50]">采集时间</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-[#2C3E50]">数据大小</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-[#2C3E50]">解析状态</th>
                <th className="px-6 py-4 text-left text-sm font-medium text-[#2C3E50]">操作</th>
              </tr>
            </thead>
            <tbody>
              {dataFiles.map((file) => (
                <tr
                  key={file.id}
                  className={`border-b border-[#E4E7ED] bg-white hover:bg-[#FAFAFA] 
                            ${file.parseStatus === 'completed' ? 'cursor-pointer' : ''}`}
                  onClick={() => file.parseStatus === 'completed' && onFileClick(file.id)}
                >
                  <td className="px-6 py-4">
                    <div>
                      <div className="text-sm text-[#2C3E50] font-medium">{file.fileName}</div>
                      {file.metadata && (
                        <div className="text-xs text-[#909399] mt-1">
                          SN: {file.metadata.serialNumber} | {file.metadata.sampleRate}Hz
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {file.deviceType === 'watch' ? (
                        <>
                          <Watch className="w-4 h-4 text-[#1890FF]" />
                          <span className="text-sm text-[#2C3E50]">手表</span>
                        </>
                      ) : (
                        <>
                          <div className="w-4 h-4 rounded-full border-2 border-[#722ED1]" />
                          <span className="text-sm text-[#2C3E50]">指环</span>
                        </>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-[#2C3E50]">{file.collectionTime}</td>
                  <td className="px-6 py-4 text-sm text-[#2C3E50]">{file.dataSize}</td>
                  <td className="px-6 py-4">
                    <div className="group relative">
                      {getStatusIcon(file.parseStatus, file.parseProgress)}
                      {file.parseStatus === 'failed' && file.errorMessage && (
                        <div className="absolute left-0 top-full mt-2 hidden group-hover:block z-10">
                          <div className="bg-[#2C3E50] text-white text-xs px-3 py-2 rounded shadow-lg max-w-xs">
                            {file.errorMessage}
                          </div>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <button
                        className="p-2 hover:bg-[#F5F7FA] rounded transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          // Download action
                        }}
                      >
                        <Download className="w-4 h-4 text-[#909399]" />
                      </button>
                      <button
                        className="p-2 hover:bg-[#FEF0F0] rounded transition-colors"
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteClick(file.id);
                        }}
                      >
                        <Trash2 className="w-4 h-4 text-[#F5222D]" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}