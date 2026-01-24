<script setup lang="ts">
import { UploadCloud, FileText, Database, CheckCircle, Clock, Loader2, X, Check } from 'lucide-vue-next';
import { useFileStore } from '../stores/fileStore';
import { fileService } from '../services/fileService';
import { ref, onMounted } from 'vue';

const fileStore = useFileStore();

// Upload state
const isDragging = ref(false);
const isUploading = ref(false);
const uploadProgress = ref(0);
const uploadStatus = ref<'idle' | 'uploading' | 'success' | 'error'>('idle');
const uploadMessage = ref('');
const fileInputRef = ref<HTMLInputElement | null>(null);

// Fetch stats on mount
onMounted(() => {
    fileStore.fetchStats();
});

// Handle file selection
const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    uploadFile(files[0]);
};

// Handle drag events
const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    isDragging.value = true;
};

const handleDragLeave = () => {
    isDragging.value = false;
};

const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    isDragging.value = false;
    handleFileSelect(e.dataTransfer?.files || null);
};

// Upload file
const uploadFile = async (file: File) => {
    // Validate extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['rawdata', 'zip'].includes(ext || '')) {
        uploadStatus.value = 'error';
        uploadMessage.value = 'Invalid file type. Use .rawdata or .zip';
        setTimeout(() => { uploadStatus.value = 'idle'; }, 3000);
        return;
    }

    isUploading.value = true;
    uploadStatus.value = 'uploading';
    uploadProgress.value = 0;
    uploadMessage.value = file.name;

    try {
        await fileService.uploadFile(file, (progress) => {
            uploadProgress.value = progress;
        });
        
        uploadStatus.value = 'success';
        uploadMessage.value = 'Upload complete!';
        
        // Refresh file list and stats
        await fileStore.fetchFiles();
        await fileStore.fetchStats();
        
        setTimeout(() => { 
            uploadStatus.value = 'idle'; 
            isUploading.value = false;
        }, 2000);
    } catch (e) {
        uploadStatus.value = 'error';
        uploadMessage.value = e instanceof Error ? e.message : 'Upload failed';
        setTimeout(() => { 
            uploadStatus.value = 'idle'; 
            isUploading.value = false;
        }, 3000);
    }
};

// Trigger file input
const triggerFileInput = () => {
    fileInputRef.value?.click();
};
</script>

<template>
  <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
    <!-- Upload Section (Left - 2/3 width) -->
    <div class="lg:col-span-7 flex flex-col">
      <h2 class="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2 px-1 h-[28px]">
          <UploadCloud :size="18" class="text-slate-400" />
          Quick Upload
      </h2>
      
      <!-- Hidden file input -->
      <input 
        type="file" 
        ref="fileInputRef"
        class="hidden" 
        accept=".rawdata,.zip"
        @change="handleFileSelect(($event.target as HTMLInputElement).files)"
      />
      
      <!-- Upload Zone -->
      <button 
        @click="triggerFileInput"
        @dragover="handleDragOver"
        @dragleave="handleDragLeave"
        @drop="handleDrop"
        :disabled="isUploading"
        class="w-full flex-1 group relative flex flex-col items-center justify-center py-6 px-4 rounded-2xl border border-dashed transition-all duration-300 shadow-sm min-h-[140px]"
        :class="[
          isDragging ? 'border-blue-500 bg-blue-50 shadow-md' : 'border-slate-300 bg-white hover:border-blue-500 hover:bg-blue-50/10 hover:shadow-md',
          isUploading ? 'cursor-wait' : 'cursor-pointer'
        ]"
      >
        <!-- Idle State -->
        <template v-if="uploadStatus === 'idle'">
          <div class="p-3 bg-blue-50 text-blue-600 rounded-full mb-3 group-hover:bg-blue-600 group-hover:text-white group-hover:scale-110 transition-all duration-300 shadow-sm shadow-blue-100">
              <UploadCloud :size="24" />
          </div>
          <h3 class="text-lg font-bold text-slate-800 mb-1 text-center">
            {{ isDragging ? 'Drop file here' : 'Upload Data' }}
          </h3>
          <p class="text-xs text-slate-400 mb-3 text-center font-medium">Support .rawdata or .zip files</p>
          <div class="flex gap-2 flex-wrap justify-center">
            <span class="text-[10px] font-semibold text-slate-500 bg-slate-100/80 px-2.5 py-1 rounded-full border border-slate-200">.rawdata</span>
            <span class="text-[10px] font-semibold text-slate-500 bg-slate-100/80 px-2.5 py-1 rounded-full border border-slate-200">.zip</span>
          </div>
        </template>
        
        <!-- Uploading State -->
        <template v-else-if="uploadStatus === 'uploading'">
          <div class="p-3 bg-blue-100 text-blue-600 rounded-full mb-3 animate-pulse">
              <Loader2 :size="24" class="animate-spin" />
          </div>
          <h3 class="text-lg font-bold text-blue-600 mb-1 text-center">Uploading...</h3>
          <p class="text-xs text-slate-500 mb-3 text-center font-medium">{{ uploadMessage }}</p>
          <div class="w-48 h-2 bg-slate-200 rounded-full overflow-hidden">
            <div 
              class="h-full bg-blue-500 transition-all duration-300"
              :style="{ width: `${uploadProgress}%` }"
            ></div>
          </div>
          <p class="text-xs text-blue-600 font-semibold mt-2">{{ uploadProgress }}%</p>
        </template>
        
        <!-- Success State -->
        <template v-else-if="uploadStatus === 'success'">
          <div class="p-3 bg-green-100 text-green-600 rounded-full mb-3">
              <Check :size="24" />
          </div>
          <h3 class="text-lg font-bold text-green-600 mb-1 text-center">{{ uploadMessage }}</h3>
        </template>
        
        <!-- Error State -->
        <template v-else-if="uploadStatus === 'error'">
          <div class="p-3 bg-red-100 text-red-600 rounded-full mb-3">
              <X :size="24" />
          </div>
          <h3 class="text-lg font-bold text-red-600 mb-1 text-center">{{ uploadMessage }}</h3>
        </template>
      </button>
    </div>

    <!-- Stats Section (Right - 1/3 width) -->
    <div class="lg:col-span-5 flex flex-col">
         <!-- Spacer to match Left Title Alignment -->
        <div class="mb-3 h-[28px] flex items-end pb-1 px-1 justify-between">
           <span class="text-xs font-semibold text-slate-400 uppercase tracking-wider">System Overview</span>
           <span class="text-[10px] text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">Updated: Just now</span>
        </div>

        <!-- Merged Stats Container -->
        <div class="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm grid grid-cols-2 md:grid-cols-4 divide-x divide-y md:divide-y-0 divide-slate-100 items-center min-h-[140px]">
            
            <div class="p-5 flex flex-col justify-center items-center h-full hover:bg-slate-50 transition-all duration-300 first:rounded-l-2xl group cursor-default">
                <div class="flex flex-col items-center gap-2 mb-1">
                    <FileText :size="18" class="text-slate-400 group-hover:text-blue-500 transition-colors" />
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 text-center">Total Files</span>
                </div>
                <div class="text-2xl font-bold text-slate-800 group-hover:scale-105 transition-transform">{{ fileStore.stats.totalFiles.toLocaleString() }}</div>
            </div>

            <div class="p-5 flex flex-col justify-center items-center h-full hover:bg-slate-50 transition-all duration-300 group cursor-default">
                <div class="flex flex-col items-center gap-2 mb-1">
                    <CheckCircle :size="18" class="text-slate-400 group-hover:text-green-500 transition-colors" />
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 text-center">Today</span>
                </div>
                <div class="text-2xl font-bold text-slate-800 group-hover:scale-105 transition-transform">{{ fileStore.stats.todayUploads }}</div>
            </div>

            <div class="p-5 flex flex-col justify-center items-center h-full hover:bg-slate-50 transition-all duration-300 group cursor-default">
                <div class="flex flex-col items-center gap-2 mb-1">
                    <Clock :size="18" class="text-slate-400 group-hover:text-amber-500 transition-colors" />
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 text-center">Pending</span>
                </div>
                <div class="text-2xl font-bold text-slate-800 group-hover:scale-105 transition-transform">{{ fileStore.stats.pendingTasks }}</div>
            </div>

            <div class="p-5 flex flex-col justify-center items-center h-full hover:bg-slate-50 transition-all duration-300 last:rounded-r-2xl group cursor-default">
                <div class="flex flex-col items-center gap-2 mb-1">
                    <Database :size="18" class="text-slate-400 group-hover:text-purple-500 transition-colors" />
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 text-center">Storage</span>
                </div>
                <div class="text-2xl font-bold text-slate-800 group-hover:scale-105 transition-transform">{{ fileStore.stats.storageUsed }}</div>
            </div>
        </div>
    </div>
  </div>
</template>
