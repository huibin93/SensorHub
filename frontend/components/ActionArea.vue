<script setup lang="ts">
import { UploadCloud, FileText, Database, CheckCircle, Clock, Loader2, X, Check } from 'lucide-vue-next';
import { useFileStore } from '../stores/fileStore';
import { fileService } from '../services/fileService';
import { ref, onMounted, onUnmounted } from 'vue';
import ZstdWorker from '../workers/zstd.worker.js?worker';

import { v4 as uuidv4 } from 'uuid';

import { workerService } from '../services/workerService';

const fileStore = useFileStore();

// Upload state
const isDragging = ref(false);
const isUploading = ref(false);
const uploadProgress = ref(0);
const uploadStatus = ref('idle');
const uploadMessage = ref('');
const fileInputRef = ref(null) as any;
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Toast State
const toasts = ref<{id: number, msg: string, type: 'error' | 'success'}[]>([]);

const addToast = (msg: string, type: 'error' | 'success' = 'error') => {
    const id = Date.now() + Math.random();
    toasts.value.push({id, msg, type});
    setTimeout(() => {
        toasts.value = toasts.value.filter(t => t.id !== id);
    }, 3000);
};

// Fetch stats on mount
onMounted(() => {
    fileStore.fetchStats();
});

// Helper to call worker with Promise (Delegate to Service)
const callWorker = (action: string, payload: any): Promise<any> => {
    return workerService.call(action, payload);
};

/**
 * Validate file content (Simple Header/Encoding Check)
 * 验证文件内容 (简单的文件头/编码检查)
 */
const validateFile = async (file: File): Promise<boolean> => {
    // 1. Read first 1KB
    // 读取前 1KB 数据
    const chunk = await file.slice(0, 1024).arrayBuffer();
    const uint8 = new Uint8Array(chunk);
    
    console.log(`[Validation] Checking file header: ${file.name}`); // 检查文件头
    
    // 2. Check for PDF Signature (%PDF)
    // 检查 PDF 签名
    if (uint8.length >= 4 && 
        uint8[0] === 0x25 && uint8[1] === 0x50 && uint8[2] === 0x44 && uint8[3] === 0x46) {
        console.warn(`[Validation] PDF Magic Number detected! Rejecting.`); // 发现 PDF 签名
        throw new Error(`Unsupported file format. Only UTF-8 encoded .rawdata files are allowed.`);
    }

    // 3. Simple Binary Check (Look for excessive null bytes)
    // 简单的二进制检查 (检查过多的空字节)
    // .rawdata should be mostly CSV/Text.
    let nullCount = 0;
    for (let i = 0; i < Math.min(uint8.length, 500); i++) {
        if (uint8[i] === 0x00) nullCount++;
    }
    
    // If >10% of start is null bytes, likely binary (except if it's UTF-16, but .rawdata is usu. UTF-8)
    // 如果前 500 字节中有超过 10% 的空字节，可能是二进制文件
    if (nullCount > 50) { 
        console.warn(`[Validation] Excessive null bytes detected (${nullCount}). Likely binary.`); // 发现过多空字节
        // We warn but maybe strict reject? User said "Check if it is utf-8 encoding"
        // Let's implement a strict check for now if it looks really binary.
        throw new Error(`Unsupported file format (Binary detected). Please provide UTF-8 encoded .rawdata.`);
    }

    console.log(`[Validation] File ${file.name} looks valid (Text-like).`); // 文件看起来是有效的文本
    return true;
};

// Handle file selection (Entry Point)
const handleFileSelect = async (files: FileList | File[] | null) => {
    if (!files || files.length === 0) return;

    // Reset UI State if not already uploading
    if (!isUploading.value) {
        uploadStatus.value = 'idle';
        uploadMessage.value = '';
        uploadProgress.value = 0;
    }

    const fileArray = Array.from(files);
    let hasValidFiles = false;
    
    try {
        for (const file of fileArray) {
            const ext = file.name.split('.').pop()?.toLowerCase();
            if (ext === 'zip') {
                hasValidFiles = true;
                if (!isUploading.value) {
                     isUploading.value = true;
                     uploadStatus.value = 'uploading';
                }
                await handleZipFile(file);
            } else if (ext === 'rawdata') {
                hasValidFiles = true;
                if (!isUploading.value) {
                     isUploading.value = true;
                     uploadStatus.value = 'uploading';
                }
                
                // Content Validation before processing
                // 处理前进行内容校验
                try {
                    await validateFile(file);
                    await processAndUpload(file);
                } catch (valErr: any) {
                    console.error(`[Validation] Skipped invalid file: ${file.name}`, valErr); // 校验失败，跳过文件
                    addToast(`Skipped ${file.name}: ${valErr.message}`, 'error');
                }
            } else {
                console.warn(`Skipped unsupported file: ${file.name}`);
                addToast(`Skipped ${file.name}: Only .rawdata or .zip allowed`, 'error');
            }
        }
        
        if (hasValidFiles) {
            // Final success state if all went well
            uploadStatus.value = 'success';
            uploadMessage.value = 'All tasks complete!';

            // Refresh Data
            await fileStore.fetchFiles();
            await fileStore.fetchStats();

            setTimeout(() => { 
                uploadStatus.value = 'idle'; 
                isUploading.value = false;
            }, 2000);
        } else if (fileArray.length === 1 && !hasValidFiles) {
             // If user selected only 1 file and it was invalid, show error on card too?
             // But Toast is enough. We can reset card.
             uploadStatus.value = 'idle'; 
        }

    } catch (e) {
        console.error(e);
        uploadStatus.value = 'error';
        uploadMessage.value = e instanceof Error ? e.message : 'Upload failed';
        addToast(uploadMessage.value, 'error');
        setTimeout(() => { 
            uploadStatus.value = 'idle'; 
            isUploading.value = false;
        }, 5000);
    }
};

// Handle ZIP processing (Serial extraction & upload)
const handleZipFile = async (zipFile: File) => {
    uploadMessage.value = `Analyzing ${zipFile.name}...`;
    const unzipStart = performance.now();
    
    // Default password from env
    const defaultPassword = import.meta.env.VITE_ZIP_PASSWORD || 'creeek666';

    try {
        // Use zip.js
        // @ts-ignore
        const { BlobReader, ZipReader, BlobWriter } = await import('@zip.js/zip.js');

        const zipReader = new ZipReader(new BlobReader(zipFile));
        const entries = await zipReader.getEntries();

        let totalUncompressedSize = 0;
        const validEntries: any[] = [];
        const fileListLog: string[] = [];

        // 1. Scan entries
        for (const entry of entries) {
            if (entry.directory) continue;
            
            // zip.js provides uncompressedSize directly
            const entrySize = entry.uncompressedSize;
            totalUncompressedSize += entrySize;
            
            fileListLog.push(`  - ${entry.filename} (${(entrySize / 1024 / 1024).toFixed(2)} MB)${entry.encrypted ? ' [Encrypted]' : ''}`);

            if (entry.filename.endsWith('.rawdata')) {
                validEntries.push(entry);
            }
        }

        // 2. Zip Bomb Protection
        const MAX_SIZE = 3 * 1024 * 1024 * 1024; // 3GB
        const MAX_RATIO = 200;
        const compressionRatio = totalUncompressedSize / (zipFile.size || 1);

        console.log(`[Zip Analysis] Input: ${zipFile.name}\n` +
            `  Size: ${(zipFile.size / 1024 / 1024).toFixed(2)} MB\n` +
            `  Uncompressed Est: ${(totalUncompressedSize / 1024 / 1024).toFixed(2)} MB\n` +
            `  Ratio: ${compressionRatio.toFixed(1)}x\n` + 
            `  Files Found:\n${fileListLog.join('\n')}`
        );

        if (totalUncompressedSize > MAX_SIZE) {
            throw new Error(`Zip Bomb Detected! Total: ${(totalUncompressedSize/1024/1024).toFixed(0)}MB > 3GB. Please unzip manually.`);
        }
        
        if (compressionRatio > MAX_RATIO && totalUncompressedSize > 100 * 1024 * 1024) {
             throw new Error(`Zip Bomb Detected! Ratio: ${compressionRatio.toFixed(0)}x. Please unzip manually.`);
        }

        if (validEntries.length === 0) {
            addToast(`No .rawdata files found in ${zipFile.name}`, 'error');
            await zipReader.close();
            return;
        }

        const unzipEnd = performance.now();
        console.log(`[Unzip] Analysis took ${(unzipEnd - unzipStart).toFixed(0)}ms`);

        // 3. Extract and Process
        let count = 0;
        for (const entry of validEntries) {
            count++;
            uploadMessage.value = `[${count}/${validEntries.length}] Unzipping ${entry.filename}...`;
            
            const extractStart = performance.now();
            let blob: Blob;

            try {
                const cleanPassword = defaultPassword.trim();
                
                // Configure zip.js to run on main thread for better error visibility
                // @ts-ignore
                if (window.zip) {
                     // @ts-ignore
                    window.zip.configure({ useWebWorkers: false });
                }

                blob = await entry.getData(new BlobWriter(), { 
                    password: entry.encrypted ? cleanPassword : undefined 
                });
            } catch (err: any) {
                // Check for password error
                if (err.message && (err.message.includes("Password") || err.message.includes("Encrypted"))) {
                    throw new Error(`解密失败: ${entry.filename} 是加密文件，且默认密码无法解密。请手动解压。`);
                }
                throw err;
            }

            const extractEnd = performance.now();
            console.log(`[Unzip] Extracted ${entry.filename} in ${(extractEnd - extractStart).toFixed(0)}ms`);

            // Clean filename
            const cleanName = entry.filename.split('/').pop() || entry.filename;
            const file = new File([blob], cleanName);
            
            await processAndUpload(file);

        }

        await zipReader.close();

    } catch (err: any) {
        console.error("[Zip Error]", err);
        let msg = err.message;
        throw new Error(`Zip error: ${msg}`);
    }
};

// Core Upload Pipeline (Single File)
const processAndUpload = async (file: File) => {
    const filename = file.name;
    console.log(`[Upload] Starting process for: ${filename}`); // 开始处理文件
    
    // 0. Fast Deduplication Check (Name + Size)
    // 快速去重检查 (文件名前置过滤)
    // 如果同名且同大小，直接跳过 MD5 计算
    uploadMessage.value = `Pre-checking ${filename}...`;
    const fastCheckUrl = `${API_BASE_URL}/files/check?filename=${encodeURIComponent(filename)}&size=${file.size}`;
    try {
        const fastRes = await fetch(fastCheckUrl);
        const fastData = await fastRes.json();
        
        if (fastData.exists && fastData.exact_match) {
             console.log(`[ActionArea] Fast Check: ${filename} (Size: ${file.size}) exists. Skipping.`);
             uploadMessage.value = `[Fast Skip] ${filename} already exists.`;
             addToast(`${filename} skipped (Fast Check)`, 'success');
             await new Promise(r => setTimeout(r, 1000));
             return;
        }
    } catch (err) {
        console.warn("[ActionArea] Fast Check failed, proceeding to MD5.", err);
    }

    uploadMessage.value = `Processing ${filename}...`;

    // 1. Compute Hash
    const hashStart = performance.now();
    const { hash } = await callWorker('calcHash', { file });
    const hashEnd = performance.now();
    console.log(`[Hash] ${filename} MD5: ${hash} (${(hashEnd - hashStart).toFixed(0)}ms)`); // MD5 计算耗时日志
    
    // 2. Check Deduplication
    // 2. Check Deduplication
    uploadMessage.value = `Checking ${filename}...`;
    // FIX: URL encode filename to handle special characters
    const checkUrl = `${API_BASE_URL}/files/check?hash=${hash}&filename=${encodeURIComponent(filename)}`;
    const checkRes = await fetch(checkUrl);
    const checkData = await checkRes.json();
    
    if (checkData.exists) {
        if (checkData.exact_match) {
             console.log(`[ActionArea] Exact match found for ${filename}. Skipping upload.`);
             uploadMessage.value = `[Skipped] ${filename} already exists.`;
             addToast(`${filename} skipped (Already exists)`, 'success');
             await new Promise(r => setTimeout(r, 1000)); // Show message briefly
             return; // STOP HERE - Do not proceed to upload
        }
        
        // Exists but different name -> Proceed (Seconds transmission)
        console.log(`[ActionArea] Content exists but name differs. Creating new reference for ${filename}.`);
        uploadMessage.value = `[Fast Link] Content exists. Linking...`;
    }

    // 3. Compress
    uploadMessage.value = `Compressing ${filename}...`;
    const compressStart = performance.now();
    const { blob: compressedBlob } = await callWorker('compress', { file, level: 6 });
    const compressEnd = performance.now();
    const duration = (compressEnd - compressStart).toFixed(0);
    const ratio = ((compressedBlob.size / file.size) * 100).toFixed(1);

    console.log(
        `[Compression] ${filename}\n` +
        `  Time: ${duration}ms\n` + 
        `  Raw: ${file.size} bytes\n` + 
        `  Compressed: ${compressedBlob.size} bytes\n` + 
        `  Ratio: ${ratio}%`
    ); // 压缩耗时与数据统计日志

    // 4. Upload
    uploadMessage.value = `Uploading ${filename}...`;
    const formData = new FormData();
    formData.append('file', compressedBlob, filename + '.zst');
    formData.append('md5', hash as string);
    formData.append('filename', filename);
    formData.append('original_size', String(file.size));
    
    const response = await fetch(`${API_BASE_URL}/files/upload`, {
        method: 'POST',
        body: formData
    });
    
    if (!response.ok) {
        throw new Error(`Failed to upload ${filename}: ${response.statusText}`);
    }

    const resData = await response.json();
    
    if (resData.data && resData.data.is_duplicate) {
        uploadMessage.value = `[Exists] ${filename} already in DB.`;
        addToast(`${filename} already exists (Skipped)`, 'success');
    } else {
        uploadMessage.value = `Uploaded ${filename}`;
        addToast(`Uploaded ${filename}`, 'success');
    }
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

const triggerFileInput = () => {
    fileInputRef.value?.click();
};

defineExpose({ handleFileSelect });
</script>

<template>
  <!-- Toast Container -->
  <div class="fixed top-20 right-6 z-50 flex flex-col gap-2 pointer-events-none sticky-toast-container">
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
         <component :is="toast.type === 'error' ? X : Check" :size="18" />
         <span class="text-sm font-medium">{{ toast.msg }}</span>
      </div>
    </TransitionGroup>
  </div>

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
        multiple
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
              :style="{ width: '100%' }" 
            ></div>
          </div>
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
