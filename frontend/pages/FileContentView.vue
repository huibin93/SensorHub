<script setup lang="ts">
import { ref, onMounted, computed, watch, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { Search, ChevronDown, ChevronUp, AlertTriangle, Loader2, HardDrive } from 'lucide-vue-next';
import { Decompress } from 'fzstd';
import { fileCacheService } from '../services/fileCacheService';

const props = defineProps<{
  id: string;
}>();

const router = useRouter();

// State
const allLines = ref<string[]>([]);
const isLoading = ref(false);
const isLoadingMore = ref(false);
const error = ref('');
const filename = ref('');
const originalSize = ref(0);
const compressedSize = ref(0);
const loadedLines = ref(0);
const hasMore = ref(true);
const loadedFromCache = ref(false);

// Performance metrics
const transferTime = ref(0);
const decompressTime = ref(0);
const totalTransferTime = ref(0);
const totalDecompressTime = ref(0);

// Search
const searchQuery = ref('');
const searchMatches = ref<number[]>([]);
const currentMatchIndex = ref(-1);

// Virtual scroll
const LINES_PER_CHUNK = 10000;
const LINE_HEIGHT = 20;
const containerRef = ref<HTMLElement>();
const scrollTop = ref(0);
const containerHeight = ref(800);

// Computed
const originalSizeMB = computed(() => {
  return (originalSize.value / (1024 * 1024)).toFixed(2);
});

const compressedSizeMB = computed(() => {
  return (compressedSize.value / (1024 * 1024)).toFixed(2);
});

const compressionRatio = computed(() => {
  if (originalSize.value === 0) return '0';
  return ((1 - compressedSize.value / originalSize.value) * 100).toFixed(1);
});

const showWarning = computed(() => {
  return originalSize.value > 10 * 1024 * 1024;
});

// Update document title
watch(filename, (newVal) => {
  if (newVal) {
    // Remove extension
    const nameWithoutExt = newVal.replace(/\.[^/.]+$/, "");
    document.title = `${nameWithoutExt} - SensorHub Analytics`;
  } else {
    document.title = 'File Viewer - SensorHub Analytics';
  }
});

const totalLines = computed(() => allLines.value.length);



const visibleStart = computed(() => Math.max(0, Math.floor(scrollTop.value / LINE_HEIGHT) - 50));
const visibleEnd = computed(() => Math.min(totalLines.value, visibleStart.value + Math.ceil(containerHeight.value / LINE_HEIGHT) + 100));

const visibleLines = computed(() => {
  return allLines.value.slice(visibleStart.value, visibleEnd.value).map((line, index) => ({
    index: visibleStart.value + index,
    content: line,
    top: (visibleStart.value + index) * LINE_HEIGHT
  }));
});

const contentHeight = computed(() => totalLines.value * LINE_HEIGHT);

// Load chunk
let decompressor: Decompress | null = null;
let accumulatedText = '';

const loadNextChunk = async () => {
  if (isLoadingMore.value) return;
  
  isLoadingMore.value = true;
  const startTime = performance.now();
  
  try {
    console.log(`[FileContent] Loading file ${props.id}...`);
    
    // Check cache first (with error handling)
    let cached = null;
    try {
      cached = await fileCacheService.get(props.id);
    } catch (err) {
      console.warn(`[FileContent] Cache access error:`, err);
      // Continue without cache
    }
    
    let compressedData: Blob;
    
    if (cached) {
      console.log(`[FileContent] Loading from cache...`);
      loadedFromCache.value = true;
      compressedData = cached.data;
      filename.value = cached.filename;
      originalSize.value = cached.originalSize;
      compressedSize.value = cached.compressedSize;
      
      const cacheLoadTime = performance.now() - startTime;
      console.log(`[FileContent] Cache hit! Loaded ${(cached.compressedSize / 1024 / 1024).toFixed(2)}MB in ${Math.round(cacheLoadTime)}ms`);
    } else {
      console.log(`[FileContent] Cache miss, fetching from network...`);
      loadedFromCache.value = false;
      
      const transferStart = performance.now();
      const response = await fetch(`/api/v1/files/${props.id}/content`);
      
      if (!response.ok) {
        throw new Error(`Failed to load: ${response.statusText}`);
      }
      
      filename.value = response.headers.get('X-File-Name') || 'Unknown';
      originalSize.value = parseInt(response.headers.get('X-Original-Size') || '0');
      compressedSize.value = parseInt(response.headers.get('X-Compressed-Size') || '0');
      
      const transferEnd = performance.now();
      transferTime.value = transferEnd - transferStart;
      totalTransferTime.value += transferTime.value;
      
      console.log(`[FileContent] File: ${filename.value}, Original: ${originalSizeMB.value}MB, Compressed: ${compressedSizeMB.value}MB, Ratio: ${compressionRatio.value}%`);
      
      if (!response.body) {
        throw new Error('Response body is null');
      }
      
      // Read all compressed data
      const reader = response.body.getReader();
      const chunks: Uint8Array[] = [];
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        chunks.push(value);
      }
      
      // Combine chunks into blob
      compressedData = new Blob(chunks as BlobPart[], { type: 'application/zstd' });
      
      // Save to cache
      try {
        await fileCacheService.set({
          fileId: props.id,
          filename: filename.value,
          data: compressedData,
          originalSize: originalSize.value,
          compressedSize: compressedSize.value,
          cachedAt: Date.now()
        });
        console.log(`[FileContent] Saved to cache`);
      } catch (err) {
        console.warn(`[FileContent] Failed to save to cache:`, err);
      }
    }
    
    // Decompress with progressive rendering
    const decompressStart = performance.now();
    
    accumulatedText = '';
    let processedLines = 0;
    const RENDER_BATCH_SIZE = 5000; // Render every 5000 lines
    
    decompressor = new Decompress((chunk) => {
      try {
        const text = new TextDecoder('utf-8', { fatal: true }).decode(chunk);
        accumulatedText += text;
        
        // Process lines in batches
        const newlineCount = (accumulatedText.match(/\n/g) || []).length;
        if (newlineCount >= RENDER_BATCH_SIZE) {
          const lines = accumulatedText.split('\n');
          const completedLines = lines.slice(0, -1); // Keep last incomplete line
          accumulatedText = lines[lines.length - 1] || '';
          
          allLines.value.push(...completedLines);
          processedLines += completedLines.length;
          loadedLines.value = allLines.value.length;
          
          // Force Vue to update DOM
          nextTick();
          
          console.log(`[FileContent] Rendered ${processedLines} lines...`);
        }
      } catch (err) {
        throw err;
      }
    });
    
    const decompressStream = new TransformStream({
      transform(chunk) {
        decompressor!.push(chunk as Uint8Array);
      },
      flush() {
        decompressor!.push(new Uint8Array(0), true);
        // Process remaining lines
        if (accumulatedText) {
          const lines = accumulatedText.split('\n');
          allLines.value.push(...lines);
          loadedLines.value = allLines.value.length;
          console.log(`[FileContent] Final render: ${allLines.value.length} total lines`);
        }
      }
    });
    
    // Convert blob to stream and decompress
    const arrayBuffer = await compressedData.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);
    
    // Stream the data in chunks for progressive decompression
    const CHUNK_SIZE = 256 * 1024; // 256KB chunks
    const readableStream = new ReadableStream({
      async start(controller) {
        for (let i = 0; i < uint8Array.length; i += CHUNK_SIZE) {
          const chunk = uint8Array.slice(i, Math.min(i + CHUNK_SIZE, uint8Array.length));
          controller.enqueue(chunk);
          // Small delay to allow UI updates
          await new Promise(resolve => setTimeout(resolve, 0));
        }
        controller.close();
      }
    });
    
    await readableStream.pipeThrough(decompressStream).pipeTo(new WritableStream());
    
    const decompressEnd = performance.now();
    decompressTime.value = decompressEnd - decompressStart;
    totalDecompressTime.value += decompressTime.value;
    
    hasMore.value = false;
    
    const totalTime = performance.now() - startTime;
    console.log(`[FileContent] Loaded ${allLines.value.length} lines in ${Math.round(totalTime)}ms (Transfer: ${Math.round(transferTime.value)}ms, Decompress: ${Math.round(decompressTime.value)}ms)`);
    
  } catch (err: any) {
    if (err.name === 'EncodingError') {
      error.value = 'File contains non-UTF-8 characters. Only UTF-8 encoded files are supported.';
    } else {
      error.value = err.message || 'Failed to load file content';
    }
    console.error('[FileContent] Load error:', err);
  } finally {
    isLoading.value = false;
    isLoadingMore.value = false;
  }
};

// Search
const performSearch = () => {
  searchMatches.value = [];
  currentMatchIndex.value = -1;
  
  if (!searchQuery.value) return;
  
  const query = searchQuery.value.toLowerCase();
  
  // Search only in loaded lines
  allLines.value.forEach((line, index) => {
    if (line.toLowerCase().includes(query)) {
      searchMatches.value.push(index);
    }
  });
  
  if (searchMatches.value.length > 0) {
    currentMatchIndex.value = 0;
    scrollToLine(searchMatches.value[0]);
  }
};

const nextMatch = () => {
  if (searchMatches.value.length === 0) return;
  currentMatchIndex.value = (currentMatchIndex.value + 1) % searchMatches.value.length;
  scrollToLine(searchMatches.value[currentMatchIndex.value]);
};

const prevMatch = () => {
  if (searchMatches.value.length === 0) return;
  currentMatchIndex.value = (currentMatchIndex.value - 1 + searchMatches.value.length) % searchMatches.value.length;
  scrollToLine(searchMatches.value[currentMatchIndex.value]);
};

const scrollToLine = (lineIndex: number) => {
  if (containerRef.value) {
    containerRef.value.scrollTop = lineIndex * LINE_HEIGHT - containerHeight.value / 2;
  }
};

const highlightLine = (lineContent: string, lineIndex: number) => {
  if (!searchQuery.value || !searchMatches.value.includes(lineIndex)) {
    return escapeHtml(lineContent);
  }
  
  const isCurrent = searchMatches.value[currentMatchIndex.value] === lineIndex;
  const className = isCurrent ? 'bg-yellow-400' : 'bg-yellow-200';
  const query = searchQuery.value;
  
  let result = '';
  let lastIndex = 0;
  const lowerLine = lineContent.toLowerCase();
  const lowerQuery = query.toLowerCase();
  
  let index = lowerLine.indexOf(lowerQuery);
  while (index !== -1) {
    result += escapeHtml(lineContent.slice(lastIndex, index));
    result += `<mark class="${className}">${escapeHtml(lineContent.slice(index, index + query.length))}</mark>`;
    lastIndex = index + query.length;
    index = lowerLine.indexOf(lowerQuery, lastIndex);
  }
  
  result += escapeHtml(lineContent.slice(lastIndex));
  return result;
};

const escapeHtml = (text: string) => {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
};

const handleScroll = (e: Event) => {
  scrollTop.value = (e.target as HTMLElement).scrollTop;
  
  // Update container height
  containerHeight.value = (e.target as HTMLElement).clientHeight;
};

const goBack = () => {
  router.push('/');
};

// Lifecycle
onMounted(() => {
  isLoading.value = true;
  loadNextChunk();
  
  if (containerRef.value) {
    containerHeight.value = containerRef.value.clientHeight;
  }
});
</script>

<template>
  <div class="flex flex-col h-screen bg-slate-50">
    <!-- Header -->
    <header class="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between gap-4 shrink-0">
      <div class="flex-1 min-w-0">
        <h1 class="text-lg font-bold text-slate-800 truncate">{{ filename || 'Loading...' }}</h1>
        <p class="text-sm text-slate-500">
          Original: {{ originalSizeMB }} MB · Compressed: {{ compressedSizeMB }} MB · Ratio: {{ compressionRatio }}%
          <span v-if="isLoading && loadedLines > 0" class="text-blue-600 font-semibold ml-2">
            · Loading... {{ loadedLines.toLocaleString() }}  lines
          </span>
          <span v-else-if="!isLoading && totalLines > 0" class="text-green-700 font-semibold ml-2">
            · Loaded {{ totalLines.toLocaleString() }} lines
          </span>
        </p>
      </div>
      
      <!-- Search -->
      <div class="flex items-center gap-2">
        <div class="relative">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" :size="16" />
          <input 
            v-model="searchQuery"
            @input="performSearch"
            type="text"
            placeholder="Search content..."
            class="pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none w-64"
          />
        </div>
        
        <div v-if="searchMatches.length > 0" class="flex items-center gap-1 text-sm text-slate-600">
          <span>{{ currentMatchIndex + 1 }} / {{ searchMatches.length }}</span>
          <button @click="prevMatch" class="p-1 hover:bg-slate-100 rounded" title="Previous">
            <ChevronUp :size="16" />
          </button>
          <button @click="nextMatch" class="p-1 hover:bg-slate-100 rounded" title="Next">
            <ChevronDown :size="16" />
          </button>
        </div>
        
        <div v-else-if="searchQuery && searchMatches.length === 0" class="text-sm text-slate-500">
          Not found
        </div>
      </div>
    </header>
    
    <!-- Warning - Show immediately for large files -->
    <div v-if="showWarning" class="bg-yellow-50 border-b border-yellow-200 px-6 py-3 flex items-center gap-2">
      <AlertTriangle :size="18" class="text-yellow-600" />
      <span class="text-sm text-yellow-800">
        Large file ({{ originalSizeMB }} MB). Loading may take some time.
      </span>
    </div>
    
    <!-- Performance Stats -->
    <div v-if="!isLoading && totalLines > 0" class="bg-blue-50 border-b border-blue-200 px-6 py-2 flex items-center gap-4 text-xs text-blue-800">
      <span v-if="loadedFromCache" class="flex items-center gap-1 font-semibold text-green-700">
        <HardDrive :size="14" />
        Loaded from cache
      </span>
      <span v-else class="flex items-center gap-1 text-slate-600">
        Network load
      </span>
      <span>Lines: {{ totalLines.toLocaleString() }}</span>
      <span>Transfer: {{ Math.round(totalTransferTime) }}ms</span>
      <span>Decompress: {{ Math.round(totalDecompressTime) }}ms</span>
      <span>Total: {{ Math.round(totalTransferTime + totalDecompressTime) }}ms</span>
    </div>
    
    <!-- Loading (only show when no data yet) -->
    <div v-if="isLoading && totalLines === 0" class="flex-1 flex items-center justify-center">
      <div class="flex flex-col items-center gap-3">
        <Loader2 :size="32" class="animate-spin text-blue-600" />
        <p class="text-slate-600">Loading and decompressing file...</p>
        <p class="text-sm text-slate-500">Compressed: {{ compressedSizeMB }} MB → Original: {{ originalSizeMB }} MB</p>
      </div>
    </div>
    
    <!-- Error -->
    <div v-else-if="error" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <p class="text-red-600 font-semibold mb-2">Load Failed</p>
        <p class="text-slate-600">{{ error }}</p>
        <button 
          @click="loadNextChunk()" 
          class="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Retry
        </button>
      </div>
    </div>
    
    <!-- Virtual Scroll Content (show as soon as we have data) -->
    <div 
      v-if="totalLines > 0" 
      ref="containerRef"
      @scroll="handleScroll"
      class="flex-1 overflow-auto bg-white mx-6 my-4 rounded-xl border border-slate-200 shadow-sm"
    >
      <div class="relative" :style="{ height: contentHeight + 'px' }">
        <div
          v-for="line in visibleLines"
          :key="line.index"
          :style="{ 
            position: 'absolute',
            top: line.top + 'px',
            left: 0,
            right: 0,
            height: LINE_HEIGHT + 'px'
          }"
          class="px-6 text-sm font-mono text-slate-800 whitespace-pre"
          v-html="highlightLine(line.content, line.index)"
        />
      </div>
    </div>
  </div>
</template>
