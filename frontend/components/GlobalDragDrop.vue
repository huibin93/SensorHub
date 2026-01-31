<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import { UploadCloud } from 'lucide-vue-next';

// 添加 enabled prop 控制是否激活拖放功能
const props = withDefaults(defineProps<{
  enabled?: boolean;
}>(), {
  enabled: true
});

const emit = defineEmits<{
  (e: 'file-dropped', files: FileList): void
}>();

const isDragging = ref(false);
const dragCounter = ref(0);

const handleDragEnter = (e: DragEvent) => {
  e.preventDefault();
  // 只在启用时显示拖放 UI
  if (!props.enabled) return;
  
  dragCounter.value++;
  if (e.dataTransfer) {
     isDragging.value = true;
  }
};

const handleDragLeave = (e: DragEvent) => {
  e.preventDefault();
  // 只在启用时处理拖放 UI
  if (!props.enabled) return;
  
  dragCounter.value--;
  if (dragCounter.value <= 0) {
    isDragging.value = false;
    dragCounter.value = 0;
  }
};

const handleDragOver = (e: DragEvent) => {
  e.preventDefault(); // 始终阻止默认行为，防止浏览器打开文件
};

// 递归遍历文件夹获取所有文件
const traverseFileTree = async (item: FileSystemEntry, path = ''): Promise<File[]> => {
  const files: File[] = [];
  
  if (item.isFile) {
    // 是文件，转换为 File 对象
    const fileEntry = item as FileSystemFileEntry;
    const file = await new Promise<File>((resolve, reject) => {
      fileEntry.file(resolve, reject);
    });
    
    // 只收集 .rawdata 和 .zip 文件
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext === 'rawdata' || ext === 'zip') {
      console.log(`[Folder Scan] Found: ${path}${file.name}`);
      files.push(file);
    }
  } else if (item.isDirectory) {
    // 是文件夹，递归遍历
    console.log(`[Folder Scan] Entering directory: ${path}${item.name}/`);
    const dirEntry = item as FileSystemDirectoryEntry;
    const dirReader = dirEntry.createReader();
    
    // 读取文件夹内容（可能需要多次读取）
    const readEntries = (): Promise<FileSystemEntry[]> => {
      return new Promise((resolve, reject) => {
        dirReader.readEntries(resolve, reject);
      });
    };
    
    let entries: FileSystemEntry[] = [];
    let batch: FileSystemEntry[];
    
    // 循环读取直到没有更多条目
    do {
      batch = await readEntries();
      entries = entries.concat(batch);
    } while (batch.length > 0);
    
    // 递归处理每个条目
    for (const entry of entries) {
      const subFiles = await traverseFileTree(entry, path + item.name + '/');
      files.push(...subFiles);
    }
  }
  
  return files;
};

const handleDrop = async (e: DragEvent) => {
  e.preventDefault(); // 始终阻止默认行为，防止浏览器打开文件
  
  // 只在启用时处理文件上传
  if (!props.enabled) return;
  
  isDragging.value = false;
  dragCounter.value = 0;
  
  if (!e.dataTransfer) return;
  
  console.log('[Drag Drop] Processing dropped items...');
  const files: File[] = [];
  
  // 检查是否使用了 DataTransferItemList（支持文件夹）
  if (e.dataTransfer.items) {
    const items = Array.from(e.dataTransfer.items);
    console.log(`[Drag Drop] Found ${items.length} item(s)`);
    
    for (const item of items) {
      if (item.kind === 'file') {
        const entry = item.webkitGetAsEntry?.();
        if (entry) {
          console.log(`[Drag Drop] Processing: ${entry.name} (${entry.isDirectory ? 'folder' : 'file'})`);
          // 使用 FileSystemEntry API 递归遍历
          const traversedFiles = await traverseFileTree(entry);
          files.push(...traversedFiles);
        } else {
          // 降级：直接获取文件
          const file = item.getAsFile();
          if (file) {
            console.log(`[Drag Drop] Direct file: ${file.name}`);
            files.push(file);
          }
        }
      }
    }
  } else if (e.dataTransfer.files.length > 0) {
    // 降级：使用传统 FileList（不支持文件夹）
    console.log('[Drag Drop] Using legacy FileList (folder not supported)');
    files.push(...Array.from(e.dataTransfer.files));
  }
  
  console.log(`[Drag Drop] Total files collected: ${files.length}`);
  
  if (files.length > 0) {
    // 创建自定义 FileList 对象
    const fileList = {
      length: files.length,
      item: (index: number) => files[index] || null,
      [Symbol.iterator]: function* () {
        for (const file of files) {
          yield file;
        }
      }
    };
    
    // 添加索引访问
    files.forEach((file, index) => {
      (fileList as any)[index] = file;
    });
    
    emit('file-dropped', fileList as any as FileList);
  }
};

// 添加事件监听器 - 始终添加以阻止浏览器默认行为
const addListeners = () => {
  window.addEventListener('dragenter', handleDragEnter);
  window.addEventListener('dragleave', handleDragLeave);
  window.addEventListener('dragover', handleDragOver);
  window.addEventListener('drop', handleDrop);
};

// 移除事件监听器
const removeListeners = () => {
  window.removeEventListener('dragenter', handleDragEnter);
  window.removeEventListener('dragleave', handleDragLeave);
  window.removeEventListener('dragover', handleDragOver);
  window.removeEventListener('drop', handleDrop);
  // 清理状态
  isDragging.value = false;
  dragCounter.value = 0;
};

onMounted(() => {
  // 始终添加监听器以阻止浏览器默认行为
  addListeners();
});

onUnmounted(() => {
  removeListeners();
});
</script>

<template>
  <Transition
    enter-active-class="transition duration-200 ease-out"
    enter-from-class="opacity-0 scale-95"
    enter-to-class="opacity-100 scale-100"
    leave-active-class="transition duration-150 ease-in"
    leave-from-class="opacity-100 scale-100"
    leave-to-class="opacity-0 scale-95"
  >
    <div 
      v-show="isDragging"
      class="fixed inset-0 z-50 flex items-center justify-center bg-blue-50/60 backdrop-blur-sm"
    >
      <!-- Dashed Border Box -->
      <div class="w-[80%] h-[80%] border-4 border-dashed border-blue-400 rounded-3xl flex flex-col items-center justify-center bg-white/40 shadow-2xl pointer-events-none">
          <div class="p-6 bg-blue-500 text-white rounded-full mb-6 shadow-lg shadow-blue-500/30 animate-bounce">
              <UploadCloud :size="48" />
          </div>
          <h2 class="text-3xl font-bold text-slate-800 mb-2">Drop files or folders to upload</h2>
          <p class="text-lg text-slate-600">Release your mouse to start uploading</p>
          <p class="text-sm text-slate-500 mt-2">Folders will be scanned for .rawdata and .zip files</p>
      </div>
    </div>
  </Transition>
</template>
