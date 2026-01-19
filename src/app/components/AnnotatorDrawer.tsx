import { useState, useRef, useEffect } from 'react';
import { ChevronLeft, Save, Download } from 'lucide-react';
import { FileDetail, AnnotationRegion, LabelType } from '@/app/types';
import { TimeSeriesChart } from './TimeSeriesChart';
import { MiniMap } from './MiniMap';
import { RegionList } from './RegionList';
import { LabelToolbox } from './LabelToolbox';
import { ChartToolbar, ToolMode } from './ChartToolbar';
import { AnnotationEditDialog } from './AnnotationEditDialog';
import { Button } from '@/app/components/ui/button';
import { motion } from 'motion/react';
import { toast } from 'sonner';

interface AnnotatorDrawerProps {
  fileDetail: FileDetail | null;
  onClose: () => void;
  labelTypes: LabelType[];
}

export function AnnotatorDrawer({ fileDetail, onClose, labelTypes: initialLabelTypes }: AnnotatorDrawerProps) {
  const [activeChannels, setActiveChannels] = useState({ acc: true, gyro: true });
  const [selectedLabels, setSelectedLabels] = useState<LabelType[]>(initialLabelTypes);
  const [annotations, setAnnotations] = useState<AnnotationRegion[]>([]);
  const [viewport, setViewport] = useState({ start: 0, end: 30 });
  const [hoveredRegionId, setHoveredRegionId] = useState<string | null>(null);
  const [autoSaveMessage, setAutoSaveMessage] = useState(false);
  const [toolMode, setToolMode] = useState<ToolMode>(null);
  const [labelTypes, setLabelTypes] = useState<LabelType[]>(initialLabelTypes);
  const [editingAnnotation, setEditingAnnotation] = useState<AnnotationRegion | null>(null);
  const [yAxisDomain, setYAxisDomain] = useState<[number, number] | null>(null);

  useEffect(() => {
    if (fileDetail) {
      setAnnotations(fileDetail.annotations);
      setViewport({ start: 0, end: Math.min(30, fileDetail.totalDuration) });
    }
  }, [fileDetail]);

  if (!fileDetail) return null;

  const formatDuration = (seconds: number) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleChannelToggle = (channel: 'acc' | 'gyro') => {
    setActiveChannels(prev => ({ ...prev, [channel]: !prev[channel] }));
  };

  const handleCreateAnnotation = (startTime: number, endTime: number) => {
    // Use first selected label
    const labelToUse = selectedLabels[0] || labelTypes[0];
    if (!labelToUse) {
      toast.error('请先选择标签类型');
      return;
    }

    const newAnnotation: AnnotationRegion = {
      id: Date.now().toString(),
      label: labelToUse.name,
      startTime: Math.min(startTime, endTime),
      endTime: Math.max(startTime, endTime),
      color: labelToUse.color,
    };

    setAnnotations(prev => [...prev, newAnnotation]);
    showAutoSaveMessage();
  };

  const handleDeleteAnnotation = (id: string) => {
    setAnnotations(prev => prev.filter(a => a.id !== id));
    showAutoSaveMessage();
  };

  const handleClearAllAnnotations = () => {
    if (confirm('确定要清空所有标注吗？')) {
      setAnnotations([]);
      showAutoSaveMessage();
      toast.success('已清空所有标注');
    }
  };

  const handleRegionClick = (region: AnnotationRegion) => {
    const duration = region.endTime - region.startTime;
    const padding = Math.max(duration * 0.3, 2); // At least 2 seconds padding
    setViewport({
      start: Math.max(0, region.startTime - padding),
      end: Math.min(fileDetail.totalDuration, region.endTime + padding),
    });
  };

  const handleRegionEdit = (region: AnnotationRegion) => {
    setEditingAnnotation(region);
  };

  const handleSaveEditedAnnotation = (editedAnnotation: AnnotationRegion) => {
    setAnnotations(prev => 
      prev.map(a => a.id === editedAnnotation.id ? editedAnnotation : a)
    );
    showAutoSaveMessage();
  };

  const showAutoSaveMessage = () => {
    setAutoSaveMessage(true);
    setTimeout(() => setAutoSaveMessage(false), 2000);
  };

  const handleAutoFitY = () => {
    // Calculate min/max for visible data
    const visibleData = fileDetail.data.filter(
      d => d.time >= viewport.start && d.time <= viewport.end
    );
    
    const accValues = visibleData.flatMap(d => [d.accX, d.accY, d.accZ]);
    const gyroValues = visibleData.flatMap(d => [d.gyroX, d.gyroY, d.gyroZ]);
    
    const allValues = [...accValues, ...gyroValues];
    const min = Math.min(...allValues);
    const max = Math.max(...allValues);
    const padding = (max - min) * 0.1;
    
    setYAxisDomain([min - padding, max + padding]);
    toast.success('已自适应Y轴');
  };

  const handleAutoAxis = () => {
    setViewport({ start: 0, end: fileDetail.totalDuration });
    setYAxisDomain(null);
    toast.success('已缩放至全貌');
  };

  const handleZoomOut = () => {
    const duration = viewport.end - viewport.start;
    const center = (viewport.start + viewport.end) / 2;
    const newDuration = Math.min(duration * 1.5, fileDetail.totalDuration);
    
    let newStart = center - newDuration / 2;
    let newEnd = center + newDuration / 2;
    
    newStart = Math.max(0, newStart);
    newEnd = Math.min(fileDetail.totalDuration, newEnd);
    
    setViewport({ start: newStart, end: newEnd });
  };

  const handleAddLabel = (label: LabelType) => {
    setLabelTypes(prev => [...prev, label]);
    toast.success('标签已添加');
  };

  const handleDeleteLabel = (labelId: string) => {
    if (confirm('确定要删除此标签吗？')) {
      setLabelTypes(prev => prev.filter(l => l.id !== labelId));
      setSelectedLabels(prev => prev.filter(l => l.id !== labelId));
      // Remove annotations with this label
      const labelToDelete = labelTypes.find(l => l.id === labelId);
      if (labelToDelete) {
        setAnnotations(prev => prev.filter(a => a.label !== labelToDelete.name));
      }
      toast.success('标签已删除');
    }
  };

  // Filter annotations based on selected labels
  const filteredAnnotations = selectedLabels.length === 0 
    ? annotations
    : annotations.filter(a => selectedLabels.some(l => l.name === a.label));

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop - Only covers 10% left side */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="w-[10vw] bg-black/50 cursor-pointer"
        onClick={onClose}
      />

      {/* Drawer */}
      <motion.div
        initial={{ x: '100%' }}
        animate={{ x: 0 }}
        exit={{ x: '100%' }}
        transition={{ type: 'spring', damping: 30, stiffness: 300 }}
        className="w-[90vw] bg-white shadow-2xl flex flex-col"
      >
        {/* Header */}
        <div className="h-[60px] border-b border-[#E4E7ED] px-6 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-4">
            <button
              onClick={onClose}
              className="p-1 hover:bg-[#F5F7FA] rounded transition-colors"
            >
              <ChevronLeft className="w-5 h-5 text-[#2C3E50]" />
            </button>
            <h2 className="text-lg font-semibold text-[#2C3E50]">
              {fileDetail.file.fileName}
            </h2>
            <div className="px-3 py-1 bg-[#F5F7FA] rounded-full text-sm text-[#909399]">
              {formatDuration(fileDetail.totalDuration)}
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Channel Toggles */}
            <div className="flex items-center gap-2">
              <button
                className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                  activeChannels.acc
                    ? 'bg-[#1890FF] text-white'
                    : 'bg-[#F5F7FA] text-[#909399]'
                }`}
                onClick={() => handleChannelToggle('acc')}
              >
                ACC
              </button>
              <button
                className={`px-4 py-1.5 rounded text-sm font-medium transition-colors ${
                  activeChannels.gyro
                    ? 'bg-[#1890FF] text-white'
                    : 'bg-[#F5F7FA] text-[#909399]'
                }`}
                onClick={() => handleChannelToggle('gyro')}
              >
                GYRO
              </button>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm">
                <Download className="w-4 h-4 mr-2" />
                导出
              </Button>
              <Button size="sm" className="bg-[#1890FF] hover:bg-[#1890FF]/90">
                <Save className="w-4 h-4 mr-2" />
                保存
              </Button>
              {autoSaveMessage && (
                <motion.span
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="text-sm text-[#52C41A]"
                >
                  已自动保存
                </motion.span>
              )}
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Workspace (75%) */}
          <div className="flex-1 flex flex-col p-6 overflow-hidden" style={{ width: '75%' }}>
            {/* Chart Toolbar */}
            <div className="mb-4">
              <ChartToolbar
                activeMode={toolMode}
                onModeChange={setToolMode}
                onAutoAxis={handleAutoAxis}
                onZoomOut={handleZoomOut}
              />
            </div>

            {/* Charts */}
            <div className="flex-1 overflow-auto">
              {activeChannels.acc && (
                <TimeSeriesChart
                  data={fileDetail.data}
                  viewport={viewport}
                  channel="acc"
                  annotations={filteredAnnotations}
                  selectedLabels={selectedLabels}
                  onCreateAnnotation={handleCreateAnnotation}
                  hoveredRegionId={hoveredRegionId}
                  toolMode={toolMode}
                  onViewportChange={setViewport}
                  yAxisDomain={yAxisDomain}
                />
              )}
              {activeChannels.gyro && (
                <TimeSeriesChart
                  data={fileDetail.data}
                  viewport={viewport}
                  channel="gyro"
                  annotations={filteredAnnotations}
                  selectedLabels={selectedLabels}
                  onCreateAnnotation={handleCreateAnnotation}
                  hoveredRegionId={hoveredRegionId}
                  toolMode={toolMode}
                  onViewportChange={setViewport}
                  yAxisDomain={yAxisDomain}
                />
              )}
            </div>

            {/* MiniMap */}
            <div className="h-[100px] mt-4 flex-shrink-0">
              <MiniMap
                data={fileDetail.data}
                totalDuration={fileDetail.totalDuration}
                viewport={viewport}
                onViewportChange={setViewport}
                annotations={annotations}
              />
            </div>
          </div>

          {/* Sidebar (25%) */}
          <div className="bg-[#FAFAFA] border-l border-[#E4E7ED] p-6 overflow-hidden flex flex-col gap-6" style={{ width: '25%' }}>
            {/* 已标注区域 - 固定 50% 高度 */}
            <div style={{ height: '50%', display: 'flex', flexDirection: 'column' }}>
              <RegionList
                annotations={filteredAnnotations}
                onDelete={handleDeleteAnnotation}
                onRegionClick={handleRegionClick}
                onHoverChange={setHoveredRegionId}
                onClearAll={handleClearAllAnnotations}
                onRegionEdit={handleRegionEdit}
              />
            </div>
            
            {/* 标签工具箱 - 固定 50% 高度 */}
            <div style={{ height: '50%', display: 'flex', flexDirection: 'column' }}>
              <LabelToolbox
                labelTypes={labelTypes}
                selectedLabels={selectedLabels}
                annotations={annotations}
                onSelectLabels={setSelectedLabels}
                onAddLabel={handleAddLabel}
                onDeleteLabel={handleDeleteLabel}
              />
            </div>
          </div>
        </div>
      </motion.div>

      {/* Edit Dialog */}
      {editingAnnotation && (
        <AnnotationEditDialog
          annotation={editingAnnotation}
          labelTypes={labelTypes}
          onClose={() => setEditingAnnotation(null)}
          onSave={handleSaveEditedAnnotation}
        />
      )}
    </div>
  );
}
