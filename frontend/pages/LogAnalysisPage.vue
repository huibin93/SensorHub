<script setup lang="ts">
/**
 * 日志分析页面
 * 支持拖放文件夹、文件或 ZIP 压缩包，筛选固件日志文件
 */
import { ref, onMounted, computed } from 'vue';
import { FileSearch, Trash2, Upload, FolderOpen, File as FileIcon, X, Loader2 } from 'lucide-vue-next';
import { useLogAnalysisStore, type LogFile } from '../stores/logAnalysisStore';
import { parseLogContent, extractLabels, isValidLogFile } from '../utils/logParser';
import LogFilePreviewDrawer from '../components/LogFilePreviewDrawer.vue';
import { v4 as uuidv4 } from 'uuid';

const logStore = useLogAnalysisStore();

// UI 状态
const isDragging = ref(false);
const isProcessing = ref(false);
const processingStatus = ref('');
const dragCounter = ref(0);

// 抽屉状态
const drawerOpen = ref(false);
const selectedFileId = ref<string | null>(null);

// Toast
const toasts = ref<{ id: number; msg: string; type: 'error' | 'success' }[]>([]);

const addToast = (msg: string, type: 'error' | 'success' = 'success') => {
  const id = Date.now() + Math.random();
  toasts.value.push({ id, msg, type });
  setTimeout(() => {
    toasts.value = toasts.value.filter(t => t.id !== id);
  }, 3000);
};

// ZIP 密码
const ZIP_PASSWORD = import.meta.env.VITE_ZIP_PASSWORD || 'creeek666';

// 初始化
onMounted(async () => {
  await logStore.init();
});

// 计算属性
const hasFiles = computed(() => logStore.files.length > 0);

// 拖放处理
const handleDragEnter = (e: DragEvent) => {
  e.preventDefault();
  dragCounter.value++;
  if (e.dataTransfer) {
    isDragging.value = true;
  }
};

const handleDragLeave = (e: DragEvent) => {
  e.preventDefault();
  dragCounter.value--;
  if (dragCounter.value <= 0) {
    isDragging.value = false;
    dragCounter.value = 0;
  }
};

const handleDragOver = (e: DragEvent) => {
  e.preventDefault();
};

// 递归遍历文件夹
const traverseFileTree = async (item: FileSystemEntry, path = ''): Promise<File[]> => {
  const files: File[] = [];
  
  if (item.isFile) {
    const fileEntry = item as FileSystemFileEntry;
    const file = await new Promise<File>((resolve, reject) => {
      fileEntry.file(resolve, reject);
    });
    files.push(file);
  } else if (item.isDirectory) {
    const dirEntry = item as FileSystemDirectoryEntry;
    const dirReader = dirEntry.createReader();
    
    const readEntries = (): Promise<FileSystemEntry[]> => {
      return new Promise((resolve, reject) => {
        dirReader.readEntries(resolve, reject);
      });
    };
    
    let entries: FileSystemEntry[] = [];
    let batch: FileSystemEntry[];
    
    do {
      batch = await readEntries();
      entries = entries.concat(batch);
    } while (batch.length > 0);
    
    for (const entry of entries) {
      const subFiles = await traverseFileTree(entry, path + item.name + '/');
      files.push(...subFiles);
    }
  }
  
  return files;
};

// 解压 ZIP（支持嵌套，最大深度 3）
const extractZip = async (zipFile: File | Blob, source: string, depth = 0): Promise<File[]> => {
  if (depth > 3) {
    console.warn(`[Zip] Max nesting depth reached for ${source}`);
    return [];
  }
  
  const files: File[] = [];
  
  try {
    // @ts-ignore
    const { BlobReader, ZipReader, BlobWriter } = await import('@zip.js/zip.js');
    
    const zipReader = new ZipReader(new BlobReader(zipFile));
    const entries = await zipReader.getEntries();
    
    for (const entry of entries) {
      if (entry.directory) continue;
      
      const filename = entry.filename.split('/').pop() || entry.filename;
      
      try {
        const blob = await entry.getData(new BlobWriter(), {
          password: entry.encrypted ? ZIP_PASSWORD.trim() : undefined
        });
        
        // 检查是否为嵌套 ZIP
        if (filename.toLowerCase().endsWith('.zip')) {
          console.log(`[Zip] Found nested ZIP: ${filename} (depth ${depth + 1})`);
          const nestedFiles = await extractZip(blob, `${source}/${filename}`, depth + 1);
          files.push(...nestedFiles);
        } else {
          const file = new File([blob], filename);
          files.push(file);
        }
      } catch (err: any) {
        console.error(`[Zip] Failed to extract ${filename}:`, err.message);
      }
    }
    
    await zipReader.close();
  } catch (err: any) {
    console.error(`[Zip] Failed to open ${source}:`, err.message);
    addToast(`Failed to open ZIP: ${err.message}`, 'error');
  }
  
  return files;
};

// 处理文件
const processFiles = async (rawFiles: File[]) => {
  isProcessing.value = true;
  processingStatus.value = 'Scanning files...';
  
  const logFiles: LogFile[] = [];
  let processed = 0;
  
  for (const file of rawFiles) {
    processed++;
    processingStatus.value = `Processing ${processed}/${rawFiles.length}: ${file.name}`;
    
    const ext = file.name.split('.').pop()?.toLowerCase();
    
    if (ext === 'zip') {
      // 解压 ZIP
      const extracted = await extractZip(file, file.name);
      
      for (const extractedFile of extracted) {
        if (isValidLogFile(extractedFile.name)) {
          const logFile = await createLogFile(extractedFile, file.name);
          if (logFile) logFiles.push(logFile);
        }
      }
    } else if (isValidLogFile(file.name)) {
      const logFile = await createLogFile(file, 'Direct Upload');
      if (logFile) logFiles.push(logFile);
    }
  }
  
  if (logFiles.length > 0) {
    processingStatus.value = 'Saving to storage...';
    await logStore.addFiles(logFiles);
    addToast(`Added ${logFiles.length} log file(s)`, 'success');
  } else {
    addToast('No valid firmware log files found', 'error');
  }
  
  isProcessing.value = false;
  processingStatus.value = '';
};

// 创建 LogFile 对象
const createLogFile = async (file: File, source: string): Promise<LogFile | null> => {
  try {
    const content = await file.text();
    const entries = parseLogContent(content);
    const labels = extractLabels(entries);
    
    return {
      id: uuidv4(),
      name: file.name,
      size: file.size,
      entries,
      labels,
      addedAt: Date.now(),
      source
    };
  } catch (err) {
    console.error(`[Parse] Failed to parse ${file.name}:`, err);
    return null;
  }
};

// 拖放处理
const handleDrop = async (e: DragEvent) => {
  e.preventDefault();
  isDragging.value = false;
  dragCounter.value = 0;
  
  if (!e.dataTransfer) return;
  
  const allFiles: File[] = [];
  
  if (e.dataTransfer.items) {
    const items = Array.from(e.dataTransfer.items);
    
    // 同步收集所有 entries
    const entries: { entry: FileSystemEntry | null; file: File | null }[] = [];
    for (const item of items) {
      if (item.kind === 'file') {
        const entry = item.webkitGetAsEntry?.();
        const file = item.getAsFile();
        entries.push({ entry, file });
      }
    }
    
    // 异步处理
    for (const { entry, file } of entries) {
      if (entry) {
        const files = await traverseFileTree(entry);
        allFiles.push(...files);
      } else if (file) {
        allFiles.push(file);
      }
    }
  } else if (e.dataTransfer.files.length > 0) {
    allFiles.push(...Array.from(e.dataTransfer.files));
  }
  
  if (allFiles.length > 0) {
    await processFiles(allFiles);
  }
};

// 打开抽屉
const openDrawer = (fileId: string) => {
  selectedFileId.value = fileId;
  drawerOpen.value = true;
};

// 关闭抽屉
const closeDrawer = () => {
  drawerOpen.value = false;
  selectedFileId.value = null;
};

// 清空所有
const handleClearAll = async () => {
  await logStore.clearAll();
  addToast('All files cleared', 'success');
};

// 格式化文件大小
const formatSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
};

// 格式化时间
const formatTime = (timestamp: number): string => {
  return new Date(timestamp).toLocaleString();
};
</script>

<template>
  <div 
    class="flex flex-col h-full bg-slate-50"
    @dragenter="handleDragEnter"
    @dragleave="handleDragLeave"
    @dragover="handleDragOver"
    @drop="handleDrop"
  >
    <!-- Toast Container -->
    <div class="fixed top-20 right-6 z-50 flex flex-col gap-2 pointer-events-none">
      <TransitionGroup
        enter-active-class="transition duration-300 ease-out"
        enter-from-class="translate-x-full opacity-0"
        enter-to-class="translate-x-0 opacity-100"
        leave-active-class="transition duration-200 ease-in"
        leave-from-class="translate-x-0 opacity-100"
        leave-to-class="translate-x-full opacity-0"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="px-4 py-3 rounded-lg shadow-lg border pointer-events-auto flex items-center gap-2 min-w-[300px]"
          :class="toast.type === 'error' ? 'bg-white border-red-100 text-red-600' : 'bg-white border-green-100 text-green-600'"
        >
          <span class="text-sm font-medium">{{ toast.msg }}</span>
        </div>
      </TransitionGroup>
    </div>

    <!-- Header -->
    <div class="px-6 py-4 border-b border-slate-200 bg-white">
      <div class="flex items-center gap-4">
        <div class="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center text-amber-600">
          <FileSearch :size="20" />
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-800">Log Analysis</h1>
          <p class="text-xs text-slate-500">Analyze firmware log files</p>
        </div>

        <div class="ml-auto flex items-center gap-3">
          <span class="text-xs text-slate-600">
            {{ logStore.totalFiles }} file(s)
          </span>
          
          <button
            v-if="hasFiles"
            @click="handleClearAll"
            class="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-red-600 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
          >
            <Trash2 :size="14" />
            Clear All
          </button>
        </div>
      </div>
    </div>

    <!-- Drop Zone (when empty or dragging) -->
    <div
      v-if="!hasFiles || isDragging"
      class="flex-1 flex items-center justify-center p-8"
      :class="isDragging ? 'bg-amber-50/50' : ''"
    >
      <div
        class="w-full max-w-xl p-12 border-2 border-dashed rounded-3xl flex flex-col items-center justify-center transition-all"
        :class="isDragging ? 'border-amber-500 bg-amber-50 scale-105' : 'border-slate-300 bg-white'"
      >
        <div
          class="p-4 rounded-full mb-4 transition-all"
          :class="isDragging ? 'bg-amber-500 text-white animate-bounce' : 'bg-amber-50 text-amber-600'"
        >
          <Upload :size="32" />
        </div>
        <h2 class="text-xl font-bold text-slate-800 mb-2">
          {{ isDragging ? 'Drop files here' : 'Drop files or folders to analyze' }}
        </h2>
        <p class="text-sm text-slate-500 text-center mb-4">
          Supports folders, .log files, and .zip archives<br/>
          <span class="text-xs text-slate-400">Files with "firmware" in name and .log extension will be analyzed</span>
        </p>
        
        <!-- Processing Status -->
        <div v-if="isProcessing" class="flex items-center gap-2 text-amber-600">
          <Loader2 :size="16" class="animate-spin" />
          <span class="text-sm font-medium">{{ processingStatus }}</span>
        </div>
      </div>
    </div>

    <!-- File List -->
    <div v-else class="flex-1 overflow-auto p-6">
      <div class="grid gap-3">
        <div
          v-for="file in logStore.files"
          :key="file.id"
          @click="openDrawer(file.id)"
          class="bg-white rounded-xl border border-slate-200 p-4 hover:border-amber-300 hover:shadow-md transition-all cursor-pointer group"
        >
          <div class="flex items-center gap-4">
            <div class="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center text-amber-600 group-hover:bg-amber-100 transition-colors">
              <FileIcon :size="20" />
            </div>
            
            <div class="flex-1 min-w-0">
              <h3 class="font-semibold text-slate-800 truncate group-hover:text-amber-600 transition-colors">
                {{ file.name }}
              </h3>
              <div class="flex items-center gap-3 text-xs text-slate-500 mt-1">
                <span>{{ formatSize(file.size) }}</span>
                <span>{{ file.entries.length }} entries</span>
                <span>{{ file.labels.length }} labels</span>
                <span>{{ formatTime(file.addedAt) }}</span>
              </div>
            </div>

            <!-- Labels Preview -->
            <div class="flex gap-1 flex-wrap max-w-xs">
              <span
                v-for="labelInfo in file.labels.slice(0, 3)"
                :key="labelInfo.label"
                class="px-2 py-1 text-[10px] font-medium bg-slate-100 text-slate-600 rounded-full"
              >
                {{ labelInfo.label }} ({{ labelInfo.count }})
              </span>
              <span
                v-if="file.labels.length > 3"
                class="px-2 py-1 text-[10px] font-medium bg-slate-100 text-slate-500 rounded-full"
              >
                +{{ file.labels.length - 3 }}
              </span>
            </div>

            <!-- Actions -->
            <button
              @click.stop="logStore.removeFile(file.id)"
              class="p-2 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
            >
              <X :size="16" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Drawer -->
    <LogFilePreviewDrawer
      :is-open="drawerOpen"
      :file-id="selectedFileId"
      @close="closeDrawer"
    />
  </div>
</template>
